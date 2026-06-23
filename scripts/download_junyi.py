#!/usr/bin/env python3
"""
download_junyi.py — §15-B：從均一教育平台抓教材純文字。

URL pattern 探勘結果（2026-06-24）：
  /topics/<english-slug>    → 領域總覽（例：/topics/math → 數學）
  /topics/<slug> 頁內有「查看課程內容」按鈕 → 課程詳情頁
  課程詳情頁內有「講義」「簡報」等 PDF / 純文字內容可抓

策略：
  1. 進 /topics/<slug> 領域總覽
  2. 抓所有「查看課程內容」按鈕的 href
  3. 進每個課程頁 → 抓純文字（講義 / 描述 / 章節列表）
  4. 寫進 textbooks/junyi/<領域>/<課程>.md + frontmatter

授權：CC BY-NC-SA 3.0 TW（Attribution + NonCommercial + ShareAlike）

Usage:
    python3 scripts/download_junyi.py --poc                # 抓 1 領域 3 課程
    python3 scripts/download_junyi.py --slug math          # 指定領域
    python3 scripts/download_junyi.py --all                # 全部領域（耗時）
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
TEXTBOOKS = ROOT / "textbooks"
TEXTBOOKS.mkdir(parents=True, exist_ok=True)

JUNYI_BASE = "https://www.junyiacademy.org"
JUNYI_LICENSE = "CC BY-NC-SA 3.0 TW"
JUNYI_LICENSE_URL = "https://www.junyiacademy.org/about/licence"

# 11 個 K12 領域 + 統一英文 slug
DOMAIN_SLUGS = [
    ("國語文", "chinese"),
    ("本土語文", "taiwanese"),
    ("英語文", "english"),
    ("數學", "math"),
    ("社會", "society"),
    ("自然科學", "science"),
    ("藝術", "art"),
    ("健康與體育", "health"),
    ("綜合活動", "comprehensive-activities"),
    ("科技", "technology"),
    ("國防", "national-defense"),
]


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def slugify(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|\s]+', '_', name.strip())
    return s[:80]


def write_textbook(course: dict, body_text: str, domain_dir: Path) -> Path:
    course_id = course.get("id", slugify(course.get("title", "unknown")))
    fname = f"{slugify(course.get('title', course_id))}.md"
    out = domain_dir / fname
    fm = {
        "title": course.get("title", ""),
        "domain": course.get("domain", ""),
        "course_id": course_id,
        "source": "均一教育平台",
        "source_url": course.get("url", ""),
        "license": JUNYI_LICENSE,
        "license_url": JUNYI_LICENSE_URL,
        "downloaded_date": now_iso(),
    }
    front_matter = "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()) + "\n---\n\n"
    header = f"# {fm['title']}\n\n> 來源：[均一教育平台]({fm['source_url']})\n> 授權：{fm['license']}（[{fm['license_url']}]({fm['license_url']})）\n> 下載時間：{fm['downloaded_date']}\n\n"
    out.write_text(front_matter + header + body_text + "\n", encoding="utf-8")
    return out


def extract_text_from_page(page) -> str:
    """從頁面 DOM 抓主要純文字內容。"""
    try:
        for sel in ["main", "article", "[role='main']", ".course-content", "#content", "body"]:
            try:
                txt = page.inner_text(sel, timeout=2000)
                if txt and len(txt) > 100:
                    return txt
            except Exception:
                continue
    except Exception as e:
        return f"[抓取失敗: {e}]"
    return ""


def discover_domain_url(page, slug: str) -> str | None:
    """自動發現某領域總覽頁 URL。try 多個變體，第一個 200 就用。
    已知 pattern：
      /topics/<slug>-elem      → 國小（最先試，因為大多領域都有國小）
      /topics/<slug>           → 領域總覽
      /topics/<slug>-juni      → 國中
      /topics/<slug>-high      → 高中
      /topics/junyi-<slug>     → 主題式
      /topics/<slug>_curriculum → 課程綱要
    """
    variants = [
        f"{slug}-elem", slug, f"{slug}-juni", f"{slug}-high",
        f"junyi-{slug}", f"{slug}_curriculum",
        f"{slug}-high-vocation", f"{slug}-univ",
    ]
    for v in variants:
        url = f"{JUNYI_BASE}/topics/{v}"
        try:
            resp = page.goto(url, timeout=4000, wait_until="domcontentloaded")
            if resp and resp.status < 400:
                log(f"    找到 {url}")
                return url
        except Exception:
            continue
    log(f"    ✗ {slug} 沒有任何 URL work")
    return None


def fetch_courses_for_domain(page, slug: str) -> list[dict]:
    """進領域總覽頁，抓所有「查看課程內容」按鈕的 href。"""
    url = discover_domain_url(page, slug)
    if not url:
        return []
    log(f"  進 {url}")
    try:
        resp = page.goto(url, timeout=20000, wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            log(f"    status {resp.status if resp else 'no resp'}, 跳過")
            return []
        page.wait_for_timeout(3000)
    except PWTimeout as e:
        log(f"    timeout: {e}")
        return []
    except Exception as e:
        log(f"    ERR: {e}")
        return []

    # 抓「查看課程內容」按鈕的 href + 父元素標題
    info = page.eval_on_selector_all(
        "a",
        """els => {
            const out = [];
            for (const e of els) {
                const text = (e.innerText || '').trim();
                if (!text.includes('查看課程內容')) continue;
                let parent = e.parentElement;
                let title = '';
                for (let i = 0; i < 5 && parent; i++) {
                    const h = parent.querySelector('h1,h2,h3,h4,h5,h6');
                    if (h && h.innerText.trim() && h.innerText.trim() !== text) {
                        title = h.innerText.trim();
                        break;
                    }
                    parent = parent.parentElement;
                }
                out.push({text, href: e.href, title});
            }
            return out;
        }"""
    )
    # 去重 + 從 URL 推 title fallback
    seen = set()
    courses = []
    for x in info:
        href = x["href"]
        if href in seen:
            continue
        seen.add(href)
        title = x["title"] or href.split("/")[-1]
        courses.append({"title": title, "href": href})
    log(f"    抓到 {len(courses)} 個課程連結")
    return courses


def main():
    parser = argparse.ArgumentParser(description="§15-B：從均一教育平台抓教材純文字")
    parser.add_argument("--poc", action="store_true", help="POC 模式：抓 1 領域 3 課程")
    parser.add_argument("--slug", type=str, help="指定英文 slug (例 math)")
    parser.add_argument("--domain", type=str, help="指定中文領域 (例 數學)")
    parser.add_argument("--all", action="store_true", help="抓全部")
    parser.add_argument("--headed", action="store_true", help="有頭模式")
    parser.add_argument("--max-courses", type=int, default=5)
    args = parser.parse_args()

    log(f"=== download_junyi.py ===")
    log(f"模式：{'POC' if args.poc else args.slug or args.domain or '全部'}")
    log(f"輸出：{TEXTBOOKS.relative_to(ROOT)}")
    log("")

    # 決定要抓的領域
    if args.poc:
        targets = [DOMAIN_SLUGS[3]]  # 數學 POC
    elif args.slug:
        targets = [(d, s) for d, s in DOMAIN_SLUGS if s == args.slug]
    elif args.domain:
        targets = [(d, s) for d, s in DOMAIN_SLUGS if d == args.domain]
    else:
        targets = DOMAIN_SLUGS

    if not targets:
        log(f"找不到匹配的領域 (slug={args.slug} domain={args.domain})")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, args=["--no-sandbox"])
        ctx = browser.new_context()
        page = ctx.new_page()

        results = []
        for domain_name, slug in targets:
            log(f"\n[領域] {domain_name} ({slug})")
            domain_dir = TEXTBOOKS / "junyi" / slugify(domain_name)
            domain_dir.mkdir(parents=True, exist_ok=True)

            courses = fetch_courses_for_domain(page, slug)
            courses = courses[:args.max_courses]

            for c in courses:
                title = c.get("title", "?")[:40]
                log(f"  [課程] {title} -> {c['href'][:80]}")
                try:
                    page.goto(c["href"], timeout=15000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
                    body = extract_text_from_page(page)
                    course = {
                        "id": c["href"].split("/")[-1] or "unknown",
                        "title": c["title"],
                        "url": c["href"],
                        "domain": domain_name,
                    }
                    out = write_textbook(course, body, domain_dir)
                    log(f"    ✓ {out.relative_to(ROOT)} ({len(body)} chars)")
                    results.append({"course": course["title"], "out": str(out.relative_to(ROOT)),
                                   "size": len(body)})
                except PWTimeout:
                    log(f"    timeout")
                except Exception as e:
                    log(f"    ERR: {type(e).__name__}: {e}")

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"寫了 {len(results)} 個教材檔")
    for r in results:
        log(f"  - {r['out']} ({r['size']} chars)")


if __name__ == "__main__":
    main()
