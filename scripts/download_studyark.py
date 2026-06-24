#!/usr/bin/env python3
"""
download_studyark.py — §16-K：抓 studyark.org 試卷。

來源：https://www.studyark.org/
結構：MediaWiki-like，每個試卷一頁 (/wiki/{id}.html)
首頁有最新試卷列表（27+ 個），標題包含完整 metadata：
  例：'市立大樹國中 七年級 109 上學期 社會領域 地理 第一次段考 期中考 翰林 試卷'

策略：
1. 進首頁抓所有 wiki 連結
2. 進每個 wiki 頁找 PDF / DOCX 連結
3. 從檔名 metadata 自動分類

POC：先抓首頁的 27 個 + 從 wiki 分頁抓更多
"""
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
import urllib.parse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
STUDYARK = ROOT / "exams" / "studyark"
STUDYARK.mkdir(parents=True, exist_ok=True)

STUDYARK_BASE = "https://www.studyark.org"


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def parse_metadata(title: str) -> dict:
    """從試卷標題解析 metadata。例：'市立大樹國中 七年級 109 上學期 社會領域 地理 第一次段考 期中考 翰林 試卷'"""
    # 學校：xxx國中/國小/高中
    school_m = re.search(r"(市立[一-鿿]{2,5}(?:國中|國小|高中)|[一-鿿]{2,5}(?:國中|國小|高中))", title)
    school = school_m.group(1) if school_m else None
    # 年級
    grade_m = re.search(r"([一二三四五六七八九])年級", title)
    grade = grade_m.group(1) + "年級" if grade_m else None
    # 學年
    year_m = re.search(r"(\d{3})學年", title)
    year = year_m.group(1) if year_m else None
    # 學期
    sem_m = re.search(r"(上|下)學期", title)
    sem = sem_m.group(1) + "學期" if sem_m else None
    # 領域
    domain_m = re.search(r"(語文領域|數學領域|自然科學領域|社會領域|綜合活動領域|健康與體育領域|藝術領域|科技領域)", title)
    domain = domain_m.group(1) if domain_m else None
    # 科目
    subj_m = re.search(r"領域\s+(.+?)\s+(第[一二三四]次段考|期中考|期末考)", title)
    subject = subj_m.group(1) if subj_m else None
    if not subject:
        # 試試另一個 pattern
        for kw in ["國文", "英文", "數學", "地理", "歷史", "公民", "自然", "理化", "生物", "物理", "化學", "地科", "生活", "健體"]:
            if kw in title:
                subject = kw
                break
    # 考試類型
    test_m = re.search(r"(第[一二三四]次段考|期中考|期末考)", title)
    test_type = test_m.group(1) if test_m else None
    # 版本
    ver_m = re.search(r"(南一|康軒|翰林|何嘉仁|龍騰|泰宇|全華|五南|旗立|佳音)", title)
    version = ver_m.group(1) if ver_m else None
    return {
        "school": school,
        "grade": grade,
        "year": year,
        "semester": sem,
        "domain": domain,
        "subject": subject,
        "test_type": test_type,
        "version": version,
    }


def fetch_studyark_index(page) -> list[dict]:
    """抓 studyark 首頁 + 試卷分頁的所有 wiki 連結。"""
    results = []
    seen_ids = set()

    # 嘗試找試卷分頁 URL
    pages_to_try = [
        STUDYARK_BASE,
        f"{STUDYARK_BASE}/test-bank",
        f"{STUDYARK_BASE}/papers",
        f"{STUDYARK_BASE}/exams",
    ]
    for url in pages_to_try:
        try:
            resp = page.goto(url, timeout=15000, wait_until="domcontentloaded")
            if not resp or resp.status >= 400:
                continue
            page.wait_for_timeout(3000)

            # 抓所有 wiki 連結
            links = page.eval_on_selector_all(
                "a[href*='/wiki/']",
                """els => els.map(e => ({
                    text: (e.innerText || '').trim(),
                    href: e.href,
                })).filter(x => x.href && x.text)"""
            )
            for l in links:
                m = re.search(r"/wiki/(\d+)", l["href"])
                if m:
                    wid = m.group(1)
                    if wid in seen_ids:
                        continue
                    seen_ids.add(wid)
                    results.append({"wiki_id": wid, "title": l["text"], "url": l["href"]})

            # 也抓「最新試卷」分頁
            for page_num in range(1, 6):  # 試 5 頁
                try:
                    page_url = f"{STUDYARK_BASE}/test-bank/page/{page_num}"
                    r2 = page.goto(page_url, timeout=10000, wait_until="domcontentloaded")
                    if not r2 or r2.status >= 400:
                        break
                    page.wait_for_timeout(2000)
                    more_links = page.eval_on_selector_all(
                        "a[href*='/wiki/']",
                        """els => els.map(e => ({
                            text: (e.innerText || '').trim(),
                            href: e.href,
                        })).filter(x => x.href && x.text)"""
                    )
                    for l in more_links:
                        m = re.search(r"/wiki/(\d+)", l["href"])
                        if m:
                            wid = m.group(1)
                            if wid in seen_ids:
                                continue
                            seen_ids.add(wid)
                            results.append({"wiki_id": wid, "title": l["text"], "url": l["href"]})
                except Exception:
                    break
        except Exception:
            continue

    return results


def fetch_wiki_page_files(ctx, wiki_id: str) -> list[dict]:
    """用真實下載 URL 抓試卷。"""
    # studyark 真實下載 URL：
    # - 試卷：/e/DownSys/download/?classid=36&id={wiki_id}
    # - 答案：/e/DownSys/download/?classid=36&id={wiki_id}&type=juan
    results = []
    for label, suffix in [("試卷", ""), ("答案", "&type=juan")]:
        url = f"{STUDYARK_BASE}/e/DownSys/download/?classid=36&id={wiki_id}{suffix}"
        try:
            resp = ctx.request.get(url, max_redirects=10)
            if resp.status == 200:
                body = resp.body()
                ct = resp.headers.get("content-type", "")
                cd = resp.headers.get("content-disposition", "")
                if body and len(body) > 500 and not body[:200].lower().startswith(b"<!doctype"):
                    # 從 Content-Disposition 抓檔名
                    fname = ""
                    m = re.search(r'filename\*?=["\']?([^"\';]+)', cd)
                    if m:
                        fname = m.group(1).split("''")[-1] if "''" in m.group(1) else m.group(1)
                        fname = urllib.parse.unquote(fname)
                    if not fname or "." not in fname:
                        ext = "pdf"
                        if "word" in ct or "officedocument" in ct:
                            ext = "docx"
                        elif "excel" in ct or "spreadsheet" in ct:
                            ext = "xls"
                        fname = f"{wiki_id}_{label}.{ext}"
                    results.append({
                        "label": label,
                        "filename": fname,
                        "url": url,
                        "content_type": ct,
                    })
        except Exception:
            pass
    return results


def download_studyark_file(ctx, url: str, fname: str, out_path: Path) -> bool:
    """下載 studyark 檔案。"""
    try:
        resp = ctx.request.get(url, max_redirects=10)
        if resp.status != 200:
            return False
        body = resp.body()
        if not body or len(body) < 500:
            return False
        if body[:200].lower().startswith(b"<!doctype"):
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(body)
        return True
    except Exception:
        return False


def main():
    log(f"=== download_studyark.py ===")
    log(f"輸出：{STUDYARK.relative_to(ROOT)}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        log("抓 studyark 試卷索引...")
        index = fetch_studyark_index(page)
        log(f"  找到 {len(index)} 個試卷\n")

        downloaded = 0
        failed = 0
        skipped = 0
        for i, item in enumerate(index):
            wiki_id = item["wiki_id"]
            title = item["title"]
            meta = parse_metadata(title)
            year = meta.get("year") or "unknown"
            grade = meta.get("grade") or "unknown"
            subject = meta.get("subject") or "unknown"
            school = meta.get("school") or "unknown"
            test_type = meta.get("test_type") or "unknown"
            sem = meta.get("semester") or "unknown"
            ver = meta.get("version") or "unknown"

            out_dir = STUDYARK / year / grade / subject / school
            log(f"  [{i+1}/{len(index)}] {title[:60]}")

            files = fetch_wiki_page_files(ctx, wiki_id)
            if not files:
                log(f"      0 檔案")
                continue

            for fl in files:
                out = out_dir / fl["filename"]
                if out.exists() and out.stat().st_size > 1000:
                    skipped += 1
                    continue
                if download_studyark_file(ctx, fl["url"], fl["filename"], out):
                    downloaded += 1
                    log(f"      ✓ {fl['label']} {fl['filename'][:40]}")
                else:
                    failed += 1
                time.sleep(0.2)

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"下載 {downloaded} 個新檔（{failed} 失敗, {skipped} 跳過）")
    log(f"輸出：{STUDYARK.relative_to(ROOT)}")


if __name__ == "__main__":
    main()


def main():
    log(f"=== download_studyark.py ===")
    log(f"輸出：{STUDYARK.relative_to(ROOT)}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        log("抓 studyark 試卷索引...")
        index = fetch_studyark_index(page)
        log(f"  找到 {len(index)} 個試卷\n")

        downloaded = 0
        failed = 0
        for i, item in enumerate(index[:30]):  # POC 只跑 30 個
            wiki_id = item["wiki_id"]
            title = item["title"]
            meta = parse_metadata(title)
            year = meta.get("year") or "unknown"
            grade = meta.get("grade") or "unknown"
            subject = meta.get("subject") or "unknown"
            school = meta.get("school") or "unknown"

            out_dir = STUDYARK / year / grade / subject / school
            log(f"  [{i+1}/{len(index)}] {title[:60]}")

            files = fetch_wiki_page_files(ctx, wiki_id)
            if not files:
                log(f"      0 檔案")
                continue

            for fl in files:
                # 構造檔名
                fname = re.sub(r'[\\/:*?"<>|]', '_', title)[:80] + ".pdf"
                out = out_dir / fname
                if out.exists() and out.stat().st_size > 1000:
                    continue
                try:
                    resp = ctx.request.get(fl["href"], max_redirects=10)
                    if resp.status == 200:
                        body = resp.body()
                        if body and len(body) > 1000 and not body[:200].lower().startswith(b"<!doctype"):
                            out_dir.mkdir(parents=True, exist_ok=True)
                            out.write_bytes(body)
                            downloaded += 1
                            log(f"      ✓ {fname[:40]}")
                except Exception:
                    failed += 1
                time.sleep(0.2)

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"下載 {downloaded} 個新 PDF（{failed} 失敗）")
    log(f"輸出：{STUDYARK.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
