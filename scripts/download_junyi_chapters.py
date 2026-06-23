#!/usr/bin/env python3
"""
download_junyi_chapters.py — §15-B v3：深入均一年級頁抓版本 → 章節內文。

從每個 textbooks/junyi/<domain>/<year>.md 的 source_url 進入年級頁，
抓「查看課程內容」（4 版本）→ 進每版本 → 抓「章節詳情」連結 → 抓內文。

POC 範圍：只做 1 個領域（數學）國小 1 年級，4 版本 × 6 章節 = 24 章節。
證明可行。完整版再做。

Usage:
    python3 scripts/download_junyi_chapters.py --poc
    python3 scripts/download_junyi_chapters.py --all
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
JUNYI_BASE = "https://www.junyiacademy.org"


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def extract_text(page) -> str:
    """抓頁面主要純文字。"""
    for sel in ["main", "article", "[role='main']", ".course-content", "#content", "body"]:
        try:
            txt = page.inner_text(sel, timeout=2000)
            if txt and len(txt) > 100:
                return txt
        except Exception:
            continue
    return ""


def fetch_chapter_content(page, chapter_url: str) -> dict:
    """進章節頁抓內容。"""
    try:
        # 用 commit 而非 domcontentloaded — 均一是 SPA，domcontentloaded 不一定觸發
        page.goto(chapter_url, timeout=15000, wait_until="commit")
        page.wait_for_timeout(3500)  # 等 SPA 渲染
        body = extract_text(page)
        if not body or len(body) < 50:
            return {"url": chapter_url, "error": f"內容太短 ({len(body) if body else 0} chars)，可能 404"}
        # 抓所有影片 / PDF 連結
        media_links = page.eval_on_selector_all(
            "a[href], iframe[src], video source",
            """els => els.map(e => ({
                kind: e.tagName,
                text: (e.innerText || '').trim().slice(0, 50),
                href: e.href || e.src || '',
            })).filter(x => x.href)"""
        )
        return {
            "url": chapter_url,
            "text": body,
            "media_links": media_links,
            "fetched_at": now_iso(),
        }
    except Exception as e:
        return {"url": chapter_url, "error": f"{type(e).__name__}: {e}"}


def process_grade_page(page, md_path: Path, version_filter: str | None = None) -> list[Path]:
    """從 .md 的 source_url 進入年級頁，抓版本 → 章節 → 內文。"""
    text = md_path.read_text(encoding="utf-8")
    fm_match = re.match(r"---\n(.+?)\n---", text, re.DOTALL)
    if not fm_match:
        log(f"    ✗ {md_path.name} 沒 frontmatter")
        return []
    source_url = re.search(r"source_url:\s*\"?([^\"\n]+)", fm_match.group(1))
    if not source_url:
        log(f"    ✗ {md_path.name} 沒 source_url")
        return []
    grade_url = source_url.group(1).strip('"')
    log(f"  進 {grade_url}")
    page.goto(grade_url, timeout=20000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # 抓「查看課程內容」按鈕 + 父元素標題（版本名）
    info = page.eval_on_selector_all(
        "a",
        """els => {
            const out = [];
            for (const e of els) {
                const text = (e.innerText || '').trim();
                if (!text.includes('查看課程內容')) continue;
                let parent = e.parentElement;
                let version = '';
                for (let i = 0; i < 6 && parent; i++) {
                    const h = parent.querySelector('h1,h2,h3,h4,h5,h6,strong,b');
                    if (h && h.innerText.trim() && h.innerText.trim() !== text) {
                        version = h.innerText.trim();
                        break;
                    }
                    parent = parent.parentElement;
                }
                out.push({version, href: e.href});
            }
            return out;
        }"""
    )
    log(f"    {len(info)} 個版本")

    if version_filter:
        info = [x for x in info if version_filter in x["version"]]
        log(f"    過濾『{version_filter}』後剩 {len(info)} 個")

    outputs = []
    domain = fm_match.group(1).split("domain:")[1].split("\n")[0].strip().strip('"')
    grade_slug = md_path.stem

    for ver in info[:2]:  # POC 只取前 2 版本
        ver_name = ver["version"][:30].replace("/", "_").replace(" ", "_")
        log(f"    版本: {ver_name} -> {ver['href']}")
        try:
            page.goto(ver["href"], timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
        except Exception as e:
            log(f"      goto ERR: {e}")
            continue

        # 抓章節連結（從版本頁 DOM）
        chapter_links = page.eval_on_selector_all(
            "a[href]",
            """els => els.map(e => ({
                text: (e.innerText || '').trim().slice(0, 50),
                href: e.href,
            })).filter(x => x.href && x.text)"""
        )
        # 過濾：章節連結（均一版用 `Chapter` 或 `第N章` 等）
        chapter_links = [c for c in chapter_links
                        if c["href"] != ver["href"]
                        and "junyiacademy.org" in c["href"]]
        # 簡單過濾：不要 footer / nav
        skip_keywords = ["關於", "捐款", "粉絲", "合作", "政策", "隱私", "登入", "搜尋"]
        chapter_links = [c for c in chapter_links
                        if not any(k in c["text"] for k in skip_keywords)]
        # 限制前 3 章節（POC）
        chapter_links = chapter_links[:3]

        log(f"      {len(chapter_links)} 章節")

        for ch in chapter_links:
            log(f"        章節: {ch['text'][:30]}")
            content = fetch_chapter_content(page, ch["href"])
            if "error" in content:
                log(f"          ERR: {content['error']}")
                continue
            # 寫 .md
            out_dir = md_path.parent / "chapters"
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_ver = slugify(ver_name)[:30]
            safe_ch = slugify(ch["text"])[:50]
            out = out_dir / f"{md_path.stem}_{safe_ver}_{safe_ch}.md"
            fm = {
                "title": ch["text"],
                "parent_md": str(md_path.relative_to(ROOT)),
                "version": ver_name,
                "domain": domain,
                "source_url": ch["href"],
                "source": "均一教育平台",
                "license": "CC BY-NC-SA 3.0 TW",
                "license_url": "https://www.junyiacademy.org/about/licence",
                "downloaded_date": now_iso(),
            }
            front = "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()) + "\n---\n\n"
            header = f"# {ch['text']} ({ver_name})\n\n> 來源：[均一教育平台]({ch['href']})\n> 授權：CC BY-NC-SA 3.0 TW\n> 父教材：{md_path.name}\n> 下載時間：{fm['downloaded_date']}\n\n"
            # 加媒體連結
            media = content.get("media_links", [])
            media_md = ""
            if media:
                media_md = "\n## 相關資源連結\n\n"
                for m in media[:20]:
                    if m["href"]:
                        media_md += f"- [{m.get('text') or m.get('kind')}]({m['href']})\n"
            out.write_text(front + header + content["text"] + media_md + "\n", encoding="utf-8")
            log(f"          ✓ {out.relative_to(ROOT)} ({len(content['text'])} chars)")
            outputs.append(out)

    return outputs


def slugify(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|\s]+', '_', name.strip())
    return s[:60]


def main():
    parser = argparse.ArgumentParser(description="§15-B v3：均一年級頁深入抓版本章節內文")
    parser.add_argument("--poc", action="store_true", help="POC：只抓數學 math-1")
    parser.add_argument("--all", action="store_true", help="全部")
    args = parser.parse_args()

    log("=== download_junyi_chapters.py ===")

    junyi = ROOT / "textbooks" / "junyi"
    if args.poc:
        # 只做 math-1 一年級
        targets = [junyi / "數學" / "math-1.md"]
    elif args.all:
        targets = sorted(junyi.rglob("*.md"))
    else:
        targets = [junyi / "數學" / "math-1.md"]

    log(f"目標：{len(targets)} 個年級 .md\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        all_outputs = []
        for md in targets:
            if not md.exists():
                continue
            log(f"\n[年級] {md.relative_to(ROOT)}")
            outputs = process_grade_page(page, md)
            all_outputs.extend(outputs)

        browser.close()

    log(f"\n=== 完成 ===")
    log(f"寫了 {len(all_outputs)} 個章節 .md")


if __name__ == "__main__":
    main()
