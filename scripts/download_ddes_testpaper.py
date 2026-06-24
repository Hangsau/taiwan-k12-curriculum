#!/usr/bin/env python3
"""
download_ddes_testpaper.py — §16-K：抓台中市大墩國小段考題庫（100-114 學年）。

來源：https://sites.google.com/ddes.tc.edu.tw/testpaper
結構：
- 每個學期頁面（如 /108/10811 = 108 上期中考）有 1 個 Google Drive embedded folder
- Folder URL 格式：drive.google.com/embeddedfolderview?id={FOLDER_ID}
- 15 學年 × 4 學期 = 60 個 Drive folder
- 每個 folder 約 12 個 PDF（6 版本 × 2 試卷類型）

抓法：對每個學期頁抓 folder ID → 進 Drive folder → 抓所有檔案下載
"""
import argparse
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
DDES = ROOT / "exams" / "ddes"
DDES.mkdir(parents=True, exist_ok=True)

DDES_BASE = "https://sites.google.com/ddes.tc.edu.tw/testpaper"

YEARS = ["100", "101", "102", "103", "104", "105", "106", "107",
         "108", "109", "110", "111", "112", "113", "114"]


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def get_drive_folder_id(page, year: str, season: str, exam: str) -> str | None:
    """進 ddes 學期頁，抓 Google Drive folder ID。"""
    page_code = f"{year}{season}{exam}"
    url = f"{DDES_BASE}/{year}/{page_code}"
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        # scroll 觸發 lazy load
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
        # 抓 embedded folder view
        m = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="drive.google.com/embeddedfolderview"]');
            if (links.length > 0) return links[0].href;
            // 也試 iframe
            const iframes = document.querySelectorAll('iframe[src*="drive.google.com"]');
            for (const f of iframes) {
                if (f.src.includes('embeddedfolderview')) return f.src;
            }
            return null;
        }""")
        if m:
            # 抓 folder ID
            fid_m = re.search(r"id=([a-zA-Z0-9_-]+)", m)
            if fid_m:
                return fid_m.group(1)
        return None
    except Exception as e:
        log(f"    ERR get folder_id: {e}")
        return None


def fetch_drive_folder_files(ctx, folder_id: str) -> list[dict]:
    """進 Drive embedded folder 抓所有檔案 + 下載。"""
    folder_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    page = ctx.new_page()
    try:
        page.goto(folder_url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)

        # 抓所有 a[href*='file/d/'] 連結（embedded folder view 的檔案呈現方式）
        files = page.eval_on_selector_all(
            "a[href*='file/d/']",
            """els => els.map(e => ({
                text: (e.innerText || '').trim(),
                href: e.href,
            })).filter(x => x.href && x.text)"""
        )

        # 去重 + 抓 FILE_ID
        seen = set()
        result = {}
        for fl in files:
            m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", fl["href"])
            if m:
                fid = m.group(1)
                if fid in seen:
                    continue
                seen.add(fid)
                fname = fl["text"] or f"{fid}.doc"
                result[fid] = fname
        return result
    except Exception as e:
        log(f"    ERR fetch: {e}")
        return {}
    finally:
        page.close()


def download_file(ctx, file_id: str, fname: str, out_dir: Path) -> Path | None:
    """下載單個 Drive 檔案。"""
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        resp = ctx.request.get(download_url, max_redirects=10)
        if resp.status != 200:
            return None
        body = resp.body()
        if not body or len(body) < 500:
            return None
        if b"<html" in body[:200].lower():
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        # 清理檔名
        fname = re.sub(r'[\\/:*?"<>|]', '_', fname)
        if "." not in fname:
            ext = "doc"  # ddes 預設是 .doc
            cd = resp.headers.get("content-disposition", "")
            ext_m = re.search(r'filename\*?=["\']?([^"\';]+)', cd)
            if ext_m:
                fn = ext_m.group(1).split("''")[-1] if "''" in ext_m.group(1) else ext_m.group(1)
                if "." in fn:
                    ext = fn.split(".")[-1]
            fname = f"{fname}.{ext}"
        out = out_dir / fname
        out.write_bytes(body)
        return out
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="§16-K：抓大墩國小段考題庫")
    parser.add_argument("--years", default="100-114", help="學年範圍")
    parser.add_argument("--max-per-page", type=int, default=20)
    args = parser.parse_args()

    if "-" in args.years:
        s, e = args.years.split("-")
        years_list = [str(y) for y in range(int(s), int(e) + 1)]
    else:
        years_list = args.years.split(",")

    log(f"=== download_ddes_testpaper.py ===")
    log(f"目標：{len(years_list)} 學年 × 4 學期 = {len(years_list)*4} 頁面")
    log(f"輸出：{DDES.relative_to(ROOT)}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        downloaded = 0
        skipped = 0
        for year in years_list:
            year_dir = DDES / year
            year_dir.mkdir(parents=True, exist_ok=True)
            for season, season_name in [("1", "上學期"), ("2", "下學期")]:
                for exam, exam_name in [("1", "期中考"), ("2", "期末考")]:
                    page_code = f"{year}{season}{exam}"
                    log(f"  {year} {season_name} {exam_name} ({page_code})")

                    folder_id = get_drive_folder_id(page, year, season, exam)
                    if not folder_id:
                        log(f"    沒 Drive folder")
                        continue

                    log(f"    folder: {folder_id[:20]}...")

                    files = fetch_drive_folder_files(ctx, folder_id)
                    if not files:
                        log(f"    0 個檔案")
                        continue

                    exam_dir = year_dir / f"{season_name}{exam_name}"

                    for fid, fname in files.items():
                        out = exam_dir / fname
                        if out.exists() and out.stat().st_size > 1000:
                            skipped += 1
                            continue
                        result = download_file(ctx, fid, fname, exam_dir)
                        if result:
                            downloaded += 1
                            log(f"      ✓ {fname[:50]}")
                        time.sleep(0.2)

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"下載 {downloaded} 個新 PDF")
    log(f"跳過 {skipped} 個已存在")
    log(f"輸出：{DDES.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
