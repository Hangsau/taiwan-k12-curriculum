#!/usr/bin/env python3
"""
download_ceec_all_years.py — §16-E：抓 108-115 學年所有大考中心試題。

策略（2026-06-24 修正）：
  GET https://www.ceec.edu.tw/xmfile?xsmsid=0J052424829869345634&Annaul=2019
  直接 URL 帶學年參數即可，不需 click submit button。
  Playwright 帶 cookie + 真實瀏覽，下載用 on('download') event。

授權：政府公開使用
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
EXAMS = ROOT / "exams"
EXAMS.mkdir(parents=True, exist_ok=True)

CEEC_BASE = "https://www.ceec.edu.tw"
CEEC_GENERAL = f"{CEEC_BASE}/xmfile?xsmsid=0J052424829869345634"

# 學年 → 西元年
YEAR_TO_ROC = {
    "108": "2019", "109": "2020", "110": "2021", "111": "2022",
    "112": "2023", "113": "2024", "114": "2025", "115": "2026",
}


def log(msg: str):
    print(msg, flush=True)


def fetch_year_page(ctx, page, year: str, exam_type: str = "gsat") -> list[dict]:
    """進年度試題頁，抓試題內容連結（page=1）。

    大考中心兩個試題 URL：
      - 學測: /xmfile?xsmsid=0J052424829869345634
      - 分科測驗/指考: /xmfile?xsmsid=0J052427633128416650

    學年切換用 form POST（Annaul=西元年）。
    用 page.context.request.post 拿 HTML response，再用 page.set_content 載入。
    """
    if exam_type == "gsat":
        xsmsid = "0J052424829869345634"
    else:  # 分科測驗/指考
        xsmsid = "0J052427633128416650"
    base_url = f"{CEEC_BASE}/xmfile?xsmsid={xsmsid}"
    roc = YEAR_TO_ROC[year]

    # 用 form.submit() + wait_for_load_state networkidle（POST 302 後 GET redirect）
    try:
        # 確保先有 cookies
        if page.url != base_url:
            page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
        # 設 select + submit form
        page.evaluate(f"() => {{ const sel = document.querySelector(\"select[name='Annaul']\"); if (sel) sel.value = '{roc}'; const form = document.querySelector('form'); if (form) form.submit(); }}")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)
    except Exception as e:
        log(f"    ERR submit: {e}")
        return []
        html = resp.text()
        # 把 response HTML 載入 page
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
    except Exception as e:
        log(f"    ERR POST: {e}")
        return []

    info = page.eval_on_selector_all(
        "a",
        """els => {
            const out = [];
            for (const e of els) {
                const text = (e.innerText || '').trim();
                if (!text.includes('試題內容')) continue;
                out.push({text, href: e.href});
            }
            return out;
        }"""
    )
    seen = set()
    unique = []
    for x in info:
        if x["href"] in seen:
            continue
        seen.add(x["href"])
        unique.append(x)
    return unique


def parse_pdf_url(href: str) -> str:
    if href.startswith("http"):
        return href
    return f"{CEEC_BASE}{href}"


def parse_year_subject(url: str) -> tuple[str, str]:
    """從 URL 解析學年 + 學科。"""
    fname_decoded = unquote(url.split("/")[-1])
    m_year = re.search(r"(\d{2,3})(?:學年|學測|分科)", fname_decoded)
    year = m_year.group(1) if m_year else "unknown"
    base = re.sub(r"^\d+-", "", fname_decoded)
    base = re.sub(r"\d+(?:學年|學測|分科).*?(?:測驗|試卷|試題)?", "", base)
    base = re.sub(r"(試卷|試題|答案)\.pdf$", "", base)
    base = re.sub(r"\.pdf$", "", base)
    subject = re.sub(r"[^\w一-鿿]", "", base)
    return year, subject


def download_pdf(ctx, url: str, out: Path) -> tuple[int, str]:
    """用 Playwright + on('download') event 抓 PDF。"""
    page = ctx.new_page()
    saved_path = [None]
    page.on("download", lambda dl: (dl.save_as(out), saved_path.__setitem__(0, out)))
    try:
        try:
            page.goto(url, timeout=30000, wait_until="commit")
        except Exception:
            pass
        page.wait_for_timeout(2500)
    finally:
        page.close()
    if saved_path[0] and saved_path[0].exists():
        return saved_path[0].stat().st_size, "ok"
    return 0, "no download event"


def main():
    parser = argparse.ArgumentParser(description="§16-E：抓 108-115 學年所有大考中心試題")
    parser.add_argument("--years", default="108-115")
    parser.add_argument("--max-per-year", type=int, default=15)
    args = parser.parse_args()

    if "-" in args.years:
        start, end = args.years.split("-")
        years_list = [str(y) for y in range(int(start), int(end) + 1)]
    else:
        years_list = args.years.split(",")

    log(f"=== download_ceec_all_years.py ===")
    log(f"目標學年：{years_list}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            accept_downloads=True,
        )
        page = ctx.new_page()

        downloaded = []
        skipped = []
        errors = []

        for year in years_list:
            for exam_type in ["gsat", "division"]:
                log(f"\n=== 學年 {year} ({exam_type}) ===")
                try:
                    links = fetch_year_page(ctx, page, year, exam_type)
                    log(f"  抓到 {len(links)} 個試題內容連結")
                except Exception as e:
                    log(f"  ERR fetch: {e}")
                    continue

                for i, l in enumerate(links[:args.max_per_year]):
                    pdf_url = parse_pdf_url(l["href"])
                    year_str, subject = parse_year_subject(pdf_url)

                    if year_str != year:
                        continue

                    is_docx = "docx" in pdf_url.lower()
                    ext = ".docx" if is_docx else ".pdf"
                    fname = f"{year}-{subject}{ext}"
                    out = EXAMS / fname

                    if out.exists() and out.stat().st_size > 1000:
                        skipped.append(fname)
                        continue

                    log(f"    [{i+1}/{min(len(links), args.max_per_year)}] 下載 {subject} → {fname}")
                    size, status = download_pdf(ctx, pdf_url, out)
                    if status == "ok":
                        log(f"      ✓ {size:,} bytes")
                        downloaded.append({"year": year, "subject": subject, "size": size,
                                           "out": str(out.relative_to(ROOT)), "exam_type": exam_type})
                    else:
                        log(f"      ERR: {status}")
                        errors.append({"year": year, "subject": subject, "status": status})

                    time.sleep(0.3)

        browser.close()

    # pdftotext
    log("\n=== pdftotext 全部 PDF ===")
    import subprocess
    for pdf in EXAMS.glob("*.pdf"):
        txt_out = EXAMS / "text" / (pdf.stem + ".txt")
        txt_out.parent.mkdir(parents=True, exist_ok=True)
        if txt_out.exists() and txt_out.stat().st_size > 100:
            continue
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt_out)],
                      capture_output=True, timeout=30)

    log(f"\n=== 完成 ===")
    log(f"下載 {len(downloaded)} 個新 PDF")
    log(f"跳過 {len(skipped)} 個已存在")
    log(f"錯誤 {len(errors)} 個")
    log(f"\n總檔案數：{len(list(EXAMS.glob('*.pdf')) + list(EXAMS.glob('*.docx')))}")
    log(f"總 text 數：{len(list((EXAMS / 'text').glob('*.txt')))}")


if __name__ == "__main__":
    main()
