#!/usr/bin/env python3
"""
download_curriculum.py — 抓 NAER 108 課綱所有 PDF，轉純文字存到 curriculum/。

URLs 從 https://www.naer.edu.tw/PageSyllabus?fid=52 (領域/科目 tab) 實際抓取。

Usage:
  python3 scripts/download_curriculum.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows cp950 console 無法輸出 ✓ 等 Unicode 符號（會 UnicodeEncodeError），強制 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent  # taiwan-k12-curriculum/
TMP_DIR = Path("/tmp/curriculum-pdf")
TMP_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://www.naer.edu.tw"

# 從 NAER 課綱總目錄實際抓取的 URL（已驗證可下載）
# 每筆：domain, name, url, date
CURRICULA = [
    # ===== 總綱 =====
    {"domain": "總綱", "name": "十二年國教課程綱要總綱", "url": "https://www.naer.edu.tw/upload/1/16/doc/288/十二年國教課程綱要總綱.pdf", "date": "103-11-28"},
    {"domain": "總綱", "name": "十二年國教課程綱要總綱（111學年度實施）", "url": "https://www.naer.edu.tw/upload/1/16/doc/288/(111學年度實施)十二年國教課程綱要總綱.pdf", "date": "110-03-15"},

    # ===== 語文領域 =====
    {"domain": "國語文", "name": "國語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/806/十二年國民基本教育課程綱要國民中小學暨普通型高級中等學校(語文領域─國語文).pdf", "date": "107-01-25"},
    {"domain": "英語文", "name": "英語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/812/(發布版)國民中小學暨普通型高級中等學校-語文領域-英語文課程綱要.pdf", "date": "107-04-16"},
    {"domain": "英語文", "name": "第二外國語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/812/(發布版)國民中學暨普通型高級中等學校-語文領域-第二外國語文課程綱要.pdf", "date": "107-04-16"},
    {"domain": "本土語文", "name": "閩南語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/1278/十二年國民基本教育課程綱要國民中小學語文領域-本土語文(閩南語文).pdf", "date": "107-03-02"},
    {"domain": "本土語文", "name": "客家語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/1280/十二年國民基本教育課程綱要國民中小學語文領域-本土語文(客家語文).pdf", "date": "107-03-02"},
    {"domain": "本土語文", "name": "原住民族語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/1282/十二年國民基本教育課程綱要國民中小學語文領域-本土語文(原住民族語文).pdf", "date": "107-03-02"},
    {"domain": "本土語文", "name": "新住民語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/1283/十二年國民基本教育課程綱要國民中小學語文領域-新住民語文.pdf", "date": "107-03-02"},
    {"domain": "本土語文", "name": "臺灣手語課程綱要", "url": "https://www.naer.edu.tw/upload/1/9/doc/3393/十二年國民基本教育課程綱要語文領域-臺灣手語-發布版.pdf", "date": "110-12-10"},
    {"domain": "本土語文", "name": "閩東語文課程綱要", "url": "https://www.naer.edu.tw/upload/1/9/doc/3444/(111學年度實施)十二年國民基本教育課程綱要語文領域-本土語文(閩東語文)-發布版.pdf", "date": "110-12-27"},

    # ===== 其他領域 =====
    {"domain": "數學", "name": "數學領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/815/十二年國民基本教育課程綱要國民中小學暨普通型高級中等學校-數學領域.pdf", "date": "107-07-26"},
    {"domain": "自然科學", "name": "自然科學領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/820/十二年國民基本教育課程綱要國民中小學暨普通型高級中等校-自然科學領域.pdf", "date": "107-11-02"},
    {"domain": "社會", "name": "社會領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/819/十二年國民基本教育課程綱要國民中小學暨普通型高級中等校-社會領域.pdf", "date": "107-10-26"},
    {"domain": "藝術", "name": "藝術領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/818/十二年國民基本教育課程綱要國民中小學暨普通型高級中等校-藝術領域.pdf", "date": "107-10-23"},
    {"domain": "綜合活動", "name": "綜合活動領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/817/十二年國民基本教育課程綱要國民中小學暨普通型高級中等校-綜合活動領域.pdf", "date": "107-10-23"},
    {"domain": "科技", "name": "科技領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/816/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf", "date": "107-09-20"},
    {"domain": "健康與體育", "name": "健康與體育領域課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/814/十二年國民基本教育課程綱要國民中小學暨普通型高級中等學校-健康與體育領域.pdf", "date": "107-06-08"},
    {"domain": "健康與體育", "name": "生活課程課程綱要（國小）", "url": "https://www.naer.edu.tw/upload/1/16/doc/813/(發布版)生活課程課程綱要.pdf", "date": "107-04-16"},
    {"domain": "國防", "name": "全民國防教育課程綱要", "url": "https://www.naer.edu.tw/upload/1/16/doc/811/十二年國民基本教育課程綱要-全民國防教育.pdf", "date": "107-03-02"},
]

# 啟布令（不抓主體，僅 metadata）
EDUCATIONAL_ORDERS = [
    {"date": "103-11-28", "name": "十二年國教總綱發布令", "url": "https://www.naer.edu.tw/upload/1/16/doc/288/103年11月28日教育部發布令.pdf"},
    {"date": "106-05-10", "name": "十二年國教總綱修正發布令", "url": "https://www.naer.edu.tw/upload/1/16/doc/288/106年5月10日教育部修正發布令.pdf"},
    {"date": "110-03-15", "name": "十二年國教總綱修正發布令（111學年度）", "url": "https://www.naer.edu.tw/upload/1/16/doc/288/110年3月15日教育部修正發布令.pdf"},
]


_PW = None
_BROWSER = None
def _get_browser():
    global _PW, _BROWSER
    if _PW is None:
        from playwright.sync_api import sync_playwright
        _PW = sync_playwright().start()
        _BROWSER = _PW.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    return _BROWSER


def download(url: str, out: Path) -> bool:
    """用 Playwright 下載 PDF（accept_downloads）。"""
    try:
        browser = _get_browser()
        ctx = browser.new_context(ignore_https_errors=True, accept_downloads=True)
        page = ctx.new_page()
        try:
            with page.expect_download(timeout=45000) as dl_info:
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                except Exception:
                    pass
            dl = dl_info.value
            dl.save_as(str(out))
            return out.exists() and out.stat().st_size > 0
        finally:
            page.close()
            ctx.close()
    except Exception as e:
        print(f"  ERR {url[:80]}: {str(e)[:80]}")
        return False


def to_text(pdf: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-layout", str(pdf), "-"],
        capture_output=True, text=True, timeout=30
    )
    return out.stdout


def save_markdown(domain: str, name: str, text: str, src_url: str, date: str) -> Path:
    domain_dir = ROOT / "curriculum" / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w]+", "_", name).strip("_")[:60]
    out_path = domain_dir / f"{slug}.md"
    frontmatter = f"""---
title: "{name}"
domain: "{domain}"
source: "國家教育研究院 (NAER)"
source_url: "{src_url}"
published_date: "{date}"
downloaded_date: "2026-06-23"
researcher: "Talos"
type: curriculum
tags: [curriculum, "108課綱"]
status: 原始文字檔，待結構化
---

# {name}

> **來源**：國家教育研究院（{date} 教育部發布）
> **URL**：<{src_url}>
> **下載日期**：2026-06-23

---

"""
    out_path.write_text(frontmatter + text, encoding="utf-8")
    return out_path


def main():
    print(f"=== 108 課綱下載器 ===")
    print(f"目標: {len(CURRICULA)} 個 PDF + {len(EDUCATIONAL_ORDERS)} 個發布令\n")

    success = 0
    failed = []
    for i, c in enumerate(CURRICULA, 1):
        safe_name = re.sub(r"[^\w]+", "_", c["name"]).strip("_")[:60]
        pdf_tmp = TMP_DIR / f"{safe_name}.pdf"
        print(f"[{i}/{len(CURRICULA)}] {c['domain']}: {c['name']}")
        if not download(c["url"], pdf_tmp):
            failed.append(c)
            continue
        text = to_text(pdf_tmp)
        if not text.strip():
            failed.append(c)
            continue
        out_path = save_markdown(c["domain"], c["name"], text, c["url"], c["date"])
        print(f"  ✓ {out_path.relative_to(ROOT)} ({len(text)} chars)")
        success += 1

    # 寫 index
    index = ROOT / "curriculum" / "_index.json"
    index_data = {
        "downloaded_date": "2026-06-23",
        "researcher": "Talos",
        "total": len(CURRICULA),
        "success": success,
        "items": [
            {
                "domain": c["domain"],
                "name": c["name"],
                "source_url": c["url"],
                "published_date": c["date"],
            } for c in CURRICULA
        ],
        "educational_orders": EDUCATIONAL_ORDERS,
    }
    index.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== 完成 ===")
    print(f"成功: {success} / {len(CURRICULA)}")
    print(f"Index: {index.relative_to(ROOT)}")
    if failed:
        print(f"失敗 ({len(failed)}):")
        for f in failed:
            print(f"  - {f['domain']}: {f['name']}")


if __name__ == "__main__":
    main()