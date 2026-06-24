#!/usr/bin/env python3
"""
download_ceec_exams.py — §16-C：下載大考中心歷年試題 PDF。

大考中心試題位於「學科能力測驗 > 歷年試題及答題卷 > 一般試題」，
需要選學年 + 學科 → 顯示 PDF 連結。JavaScript 觸發（curl 直接抓不到 PDF URL）。

策略：進「一般試題」頁，模擬 click 各學年 + 各學科，從跳轉頁抓 PDF URL。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
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


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def fetch_exam_links(page) -> list[dict]:
    """從「一般試題」頁抓所有「試題內容」連結 + 學年/學科。"""
    page.goto(CEEC_GENERAL, timeout=20000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    # 抓每個學年 + 學科的「試題內容」連結
    info = page.eval_on_selector_all(
        "a",
        """els => {
            const out = [];
            for (const e of els) {
                const text = (e.innerText || '').trim();
                if (!text.includes('試題內容')) continue;
                // 往上找最近的 tr 或 li 取學年/學科
                let parent = e.parentElement;
                let meta = '';
                for (let i = 0; i < 6 && parent; i++) {
                    const row = parent.closest('tr, li');
                    if (row) {
                        meta = row.innerText.replace(/\\s+/g, ' ').slice(0, 200);
                        break;
                    }
                    parent = parent.parentElement;
                }
                out.push({text, href: e.href, meta});
            }
            return out;
        }"""
    )
    return info


def fetch_pdf_url_from_link(page, link_text: str, meta: str) -> str | None:
    """模擬 click「試題內容」連結（如果直接 URL 不帶 PDF，click 後跳轉頁會顯示）。"""
    # 嘗試直接訪問連結，看是不是直接 PDF
    for a in page.query_selector_all("a"):
        text = a.inner_text().strip() if a.is_visible() else ""
        if link_text in text and a.is_visible():
            href = a.get_attribute("href")
            if href and ".pdf" in href.lower():
                return href
            # 不是直接 PDF，click 看跳轉頁
            try:
                a.click(timeout=3000)
                page.wait_for_timeout(3000)
                # 抓新頁面 PDF 連結
                pdf_links = page.eval_on_selector_all(
                    "a[href*='.pdf']",
                    "els => els.map(e => ({text: (e.innerText || '').trim(), href: e.href}))"
                )
                if pdf_links:
                    return pdf_links[0]["href"]
            except Exception:
                pass
    return None


def main():
    parser = argparse.ArgumentParser(description="§16-C：下載大考中心歷年試題")
    parser.add_argument("--year", type=str, help="指定學年（例 115 = 115 學年度）")
    parser.add_argument("--subject", type=str, help="指定學科（例 數學A / 英文）")
    parser.add_argument("--all", action="store_true", help="抓全部")
    parser.add_argument("--max", type=int, default=20, help="最多抓幾個")
    parser.add_argument("--pdf-only", action="store_true", help="只列 PDF URL 不下載")
    args = parser.parse_args()

    log("=== download_ceec_exams.py ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        log("進「一般試題」抓連結列表...")
        links = fetch_exam_links(page)
        log(f"找到 {len(links)} 個「試題內容」連結")

        # 過濾
        if args.year:
            links = [l for l in links if args.year in l["meta"]]
        if args.subject:
            links = [l for l in links if args.subject in l["meta"]]

        # 去重（同一考試可能多個「試題內容」連結）
        seen = set()
        unique = []
        for l in links:
            key = l["href"]
            if key in seen:
                continue
            seen.add(key)
            unique.append(l)
        links = unique[:args.max]

        log(f"過濾後剩 {len(links)} 個")
        for l in links[:10]:
            log(f"  [{l['text']!r}] meta={l['meta'][:60]!r} href={l['href'][:80]}")

        if args.pdf_only:
            log("\n（--pdf-only 模式，不下載）")
            browser.close()
            return

        downloaded = []
        for l in links:
            log(f"\n[{l['text']}] {l['meta'][:80]}")
            # 解析學年 + 學科 + 試題類型
            m = re.search(r"(\d+)學年度", l["meta"])
            year = m.group(1) if m else "unknown"
            m2 = re.search(r"－(.+?)(?:－|$|測驗|試題)", l["meta"])
            subject = m2.group(1).strip() if m2 else "unknown"
            subject = re.sub(r"[^\w一-鿿]", "_", subject)

            # 模擬 click 看 PDF URL
            pdf_url = None
            # 直接用 l["href"] — 它已經是 PDF URL（href 包含 file_pool）
            pdf_url = l["href"]
            if pdf_url.startswith("/"):
                pdf_url = f"{CEEC_BASE}{pdf_url}"

            # 解析學年/學科
            from urllib.parse import unquote
            fname_decoded = unquote(pdf_url.split("/")[-1])
            # 例：「01-115學測國綜試卷.pdf」→ year=115, subj=國綜
            # 例：「04-115學年度學科能力測驗數學A.pdf」→ year=115, subj=數學A
            m_year = re.search(r"(\d{2,3})學(?:年|測)", fname_decoded)
            year = m_year.group(1) if m_year else "unknown"
            # 從檔名末段抓學科
            m_subj = re.search(r"(?:學年|學測)[^\d]*?(?:試卷|測驗)?[^\d]*?([一-鿿]+[A-Za-z]?)(?:試卷|試題|答案|\.pdf)",
                              fname_decoded)
            if not m_subj:
                # 簡化版：抓檔名第一個中文段
                parts = re.findall(r"[一-鿿]+[A-Za-z]?", fname_decoded)
                subject = parts[0] if parts else "unknown"
            else:
                subject = m_subj.group(1)
            # 清理
            subject = re.sub(r"(試卷|試題|答案)$", "", subject)

            fname = f"{year}-{subject}.pdf"
            out = EXAMS / fname
            if out.exists() and out.stat().st_size > 10000:
                log(f"  [skip] {fname} 已存在 ({out.stat().st_size:,} bytes)")
                continue

            log(f"  下載 {subject} ({year}) → {fname}")

            # 用 Playwright（帶 cookie + 真實瀏覽）下載 — 攔截 download event
            dl_page = ctx.new_page()
            saved_path = None
            suggested_name = None
            def on_download(dl):
                nonlocal saved_path, suggested_name
                suggested_name = dl.suggested_filename
                # 保留原始副檔名（pdf / docx 都收）
                if suggested_name.endswith(".docx"):
                    target = EXAMS / fname.replace(".pdf", ".docx")
                else:
                    target = out
                dl.save_as(target)
                saved_path = target
            dl_page.on("download", on_download)

            try:
                dl_page.goto(pdf_url, timeout=30000, wait_until="commit")
                dl_page.wait_for_timeout(3000)  # 等下載完成
            except Exception as e:
                # 「Download is starting」是預期的（表示 server 回 Content-Disposition: attachment）
                if "Download" not in str(e):
                    log(f"    ERR: {type(e).__name__}: {str(e)[:80]}")
                    continue

            # 等下載事件處理完
            dl_page.wait_for_timeout(2000)

            if saved_path and saved_path.exists() and saved_path.stat().st_size > 1000:
                size = saved_path.stat().st_size
                log(f"    ✓ {size:,} bytes ({suggested_name})")
                downloaded.append({"url": pdf_url, "out": str(saved_path.relative_to(ROOT)),
                                "size": size, "year": year, "subject": subject,
                                "format": suggested_name.split(".")[-1] if suggested_name else "pdf"})
            else:
                log(f"    ERR 下載未完成 (saved_path={saved_path})")
            dl_page.close()

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"下載 {len(downloaded)} 個 PDF")
    for d in downloaded:
        log(f"  - {d['out']} ({d['size']:,} bytes)")


if __name__ == "__main__":
    main()
