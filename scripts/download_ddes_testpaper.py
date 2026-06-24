#!/usr/bin/env python3
"""
download_ddes_testpaper.py — §16-K：抓台中市大墩國小段考題庫（100-114 學年）。

來源：https://sites.google.com/ddes.tc.edu.tw/testpaper
已知結構：每個學年 4 個考試（期中考/期末考 × 上/下學期）
檔案下載方式：每個學期頁面內有「檔名代碼說明」+ 列出每個版本的試卷/解答 PDF
需要進到子頁（如 /testpaper/108/10811 = 108 上期中考）找實際檔案

POC：抓 114 學年全部 4 個考試
"""
import re
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
DDES = ROOT / "exams" / "ddes"
DDES.mkdir(parents=True, exist_ok=True)

DDES_BASE = "https://sites.google.com/ddes.tc.edu.tw/testpaper"

# 學年 → 期間連結 (從首頁抓到的)
# {year}/1{season} = 上學期 (上學期) {season}: 1=期中考, 2=期末考
YEARS = ["100", "101", "102", "103", "104", "105", "106", "107",
         "108", "109", "110", "111", "112", "113", "114"]


def main():
    print(f"=== download_ddes_testpaper.py ===")
    print(f"目標：{len(YEARS)} 個學年 × 4 個考試 = {len(YEARS)*4} 個頁面")
    print(f"輸出：{DDES.relative_to(ROOT)}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        total = 0
        for year in YEARS:
            year_dir = DDES / year
            year_dir.mkdir(parents=True, exist_ok=True)
            for season in ["1", "2"]:  # 1=上學期, 2=下學期
                for exam in ["1", "2"]:  # 1=期中考, 2=期末考
                    page_code = f"{year}{season}{exam}"
                    url = f"{DDES_BASE}/{year}/{page_code}"
                    print(f"  {year} {'上' if season == '1' else '下'} {'期中考' if exam == '1' else '期末考'} → {url[:80]}")
                    try:
                        resp = page.goto(url, timeout=15000, wait_until="domcontentloaded")
                        page.wait_for_timeout(2000)
                        if not resp or resp.status >= 400:
                            print(f"      ERR status {resp.status if resp else '?'}")
                            continue

                        # 抓所有檔案連結
                        links = page.eval_on_selector_all(
                            "a[href]",
                            """els => els.map(e => ({
                                text: (e.innerText || '').trim().slice(0, 80),
                                href: e.href,
                            })).filter(x => x.href)"""
                        )
                        file_links = [l for l in links
                                     if ".pdf" in l["href"].lower() or
                                        ".docx" in l["href"].lower() or
                                        ".doc" in l["href"].lower() or
                                        "drive.google.com" in l["href"].lower()]
                        # 也抓 drive.google.com 連結
                        drive_links = [l for l in links
                                     if "drive.google.com" in l["href"].lower()]

                        # 過濾
                        seen = set()
                        unique_files = []
                        for fl in file_links + drive_links:
                            if fl["href"] in seen:
                                continue
                            seen.add(fl["href"])
                            unique_files.append(fl)

                        if not unique_files:
                            print(f"      0 個檔案")
                            continue

                        # 對每個檔案用 page.goto + click 下載
                        for fl in unique_files[:5]:  # 限制 5 個 per page
                            try:
                                dl_page = ctx.new_page()
                                try:
                                    dl_page.goto(fl["href"], timeout=15000, wait_until="commit")
                                    dl_page.wait_for_timeout(2000)
                                except Exception:
                                    pass
                                finally:
                                    dl_page.close()
                            except Exception:
                                pass

                        print(f"      {len(unique_files)} 個檔案（已 click）")
                        total += len(unique_files)
                    except Exception as e:
                        print(f"      ERR: {type(e).__name__}: {e}")

                    time.sleep(0.5)

        browser.close()

    print(f"\n=== 完成 ===")
    print(f"總 click {total} 個檔案（實際下載要看頁面內容）")
    print(f"輸出：{DDES.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
