#!/usr/bin/env python3
"""
download_studyark.py — §16-K：抓 studyark.org（學習方舟：20158 份中小學試卷）。

來源：https://www.studyark.org/
結構（之前探索）：
- 國小 1-6 + 國中 7-9 + 高中 1-3
- 108-113 學年
- 上/下學期
- 14 科目
- 6 版本
- 有/無答案
- 期中考/期末考

首頁有搜尋功能。對每個 (學年, 學期, 科目) 搜尋 + 抓檔案下載。
"""
import re
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
STUDYARK = ROOT / "exams" / "studyark"
STUDYARK.mkdir(parents=True, exist_ok=True)

STUDYARK_BASE = "https://www.studyark.org"

# 國小 1-6 + 國中 7-9 + 高中 1-3 = 12 個年級
GRADES = list(range(1, 11))  # 1-10
SUBJECTS = ["國文", "英文", "數學", "社會", "自然", "生活", "健體"]
YEARS = ["108", "109", "110", "111", "112", "113"]
SEMESTERS = ["上", "下"]
TEST_TYPES = ["期中考", "期末考"]


def main():
    print(f"=== download_studyark.py ===")
    print(f"目標：{len(GRADES)} 年級 × {len(SUBJECTS)} 科目 × {len(YEARS)} 學年 × 2 學期 × 2 考試")
    print(f"輸出：{STUDYARK.relative_to(ROOT)}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        # 先看 search URL pattern
        page.goto(STUDYARK_BASE, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # 抓首頁所有連結看 search pattern
        links = page.eval_on_selector_all(
            "a[href]",
            """els => els.map(e => ({
                text: (e.innerText || '').trim().slice(0, 50),
                href: e.href,
            })).filter(x => x.href)"""
        )
        print(f"  首頁連結 {len(links)} 個")
        # 找搜尋相關
        search_links = [l for l in links if "search" in l["href"].lower() or "搜尋" in l["text"]]
        for l in search_links[:5]:
            print(f"    [{l['text']!r}] -> {l['href']}")

        # 嘗試找「試卷」/「題目」分頁
        exam_links = [l for l in links
                      if any(k in l["text"] for k in ["試題", "題目", "段考", "考試", "考古", "題庫", "下載"])]
        print(f"\n  試卷相關連結 ({len(exam_links)}):")
        for l in exam_links[:10]:
            print(f"    [{l['text']!r}] -> {l['href']}")

        # 進「試卷」分頁
        for path in ["/papers", "/exams", "/tests", "/test-bank", "/test_paper",
                     "/testpaper", "/tests-page", "/archive"]:
            try:
                r = page.goto(f"{STUDYARK_BASE}{path}", timeout=10000, wait_until="domcontentloaded")
                if r and r.status < 400:
                    t = page.title()
                    txt = page.inner_text("body")
                    print(f"\n  ✓ {path} (status {r.status}, {t[:40]}): {len(txt)} chars 前 200: {txt[:200]}")
            except Exception:
                pass

        browser.close()

    print(f"\n=== 探索完成 ===")
    print(f"studyark 結構複雜，需要更多探索。建議從首頁「試卷專區」入手。")


if __name__ == "__main__":
    main()
