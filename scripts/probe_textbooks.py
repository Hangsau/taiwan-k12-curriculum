#!/usr/bin/env python3
"""
probe_textbooks.py — P2 部編本覆蓋率探勘腳本。

目的：跑一輪 URL probe，確認「哪些階段 × 哪些領域」在 NAER / 教育部還找得到
合法的部編本純文字源（不下載內容，只驗可達性 + 是否還在維護）。

設計原則：
- 不下載任何教科書內容（純探 URL，避版權）
- 只跑 HEAD request，必要時 GET 首頁（限 50KB）
- 輸出 markdown 表格，方便人工 review
- idempotent：可重跑，結果寫到 plans/P2-probe-results-<date>.md

探勘對象：
- NAER 教科書圖書館（書目查詢入口）
- NAER 教科書審定專區
- 教育部教科書 / 教學資源相關頁面

注意：
- 108 課綱後多數領域已委由民間編寫（審定版），部編本可能只佔少數
- 探勘結果僅供決策 textbooks/ 結構用，不替代實際下載驗證

Usage:
    python3 scripts/probe_textbooks.py                # 跑預設探勘清單
    python3 scripts/probe_textbooks.py --headed       # 也 GET 首頁（驗內容存在）
    python3 scripts/probe_textbooks.py --json         # 輸出 JSON 而非 markdown
"""
import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
PLANS = ROOT / "plans"
PLANS.mkdir(exist_ok=True)


# 探勘清單（初版，待 user 補）
# (階段, 領域, URL, 來源類型, 備註)
SOURCES = [
    # --- NAER 教科書圖書館（書目查詢入口，按 domain 切換學制）---
    ("全", "全", "https://webpac.naer.edu.tw/?domain=6",
     "NAER 教科書圖書館（書目查詢入口）", "入口頁，需互動查詢"),
    ("全", "全", "https://www.naer.edu.tw/PageDoc?fid=26",
     "NAER 教科書審定專區", "審定資訊，非教科書本身"),
    # --- 教育部教學資源（高中）---
    ("高中", "全", "https://ghresource.k12ea.gov.tw/",
     "國教署 普通型高中學科資源平臺", "已知可用 — 教科書 PDF 來源"),
    # --- 國家圖書館（備援）---
    ("全", "全", "https://ref.ncl.edu.tw/",
     "國家圖書館參考服務", "備援來源"),
    # --- 待 user 補的：各領域各階段專屬 NAER 頁面 ---
    # 例：（國小, 國語文, https://www.naer.edu.tw/PageSyllabus?fid=XX, "部編本", ...）
]


HEADERS = {
    "User-Agent": "taiwan-k12-curriculum-probe/1.0 (+https://github.com/Hangsau/taiwan-k12-curriculum)",
    "Accept": "text/html,application/xhtml+xml",
}


def probe_url(url: str, timeout: int = 15, no_verify_ssl: bool = False) -> dict:
    """跑 HEAD request 探 URL，回傳 status / content_type / size / error。"""
    req = urllib.request.Request(url, method="HEAD", headers=HEADERS)
    context = ssl._create_unverified_context() if no_verify_ssl else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return {
                "url": url,
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": resp.headers.get("Content-Length"),
                "server": resp.headers.get("Server", ""),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "content_type": "", "content_length": None, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"url": url, "status": None, "content_type": "", "content_length": None, "error": f"URL: {e.reason}"}
    except Exception as e:
        return {"url": url, "status": None, "content_type": "", "content_length": None, "error": f"{type(e).__name__}: {e}"}


def fetch_first_n_kb(url: str, max_kb: int = 50, timeout: int = 15,
                     no_verify_ssl: bool = False) -> str | None:
    """GET 首頁限 max_kb bytes（避下載整個 PDF / 大檔），回傳純文字。"""
    req = urllib.request.Request(url, method="GET", headers=HEADERS)
    context = ssl._create_unverified_context() if no_verify_ssl else None
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            data = resp.read(max_kb * 1024)
            return data.decode("utf-8", errors="replace")
    except Exception:
        return None


def detect_textbook_keywords(text: str) -> dict:
    """從首頁 HTML 文字偵測是否有部編本 / 課綱關鍵字，回報命中。"""
    if not text:
        return {}
    keys = ["部編本", "國編本", "部定本", "審定版", "十二年國教", "108 課綱",
            "領域課程綱要", "教科書", "教材"]
    found = {k: text.count(k) for k in keys if k in text}
    return found


def main():
    parser = argparse.ArgumentParser(description="P2 部編本覆蓋率探勘")
    parser.add_argument("--headed", action="store_true",
                        help="也 GET 首頁（限 50KB）偵測關鍵字")
    parser.add_argument("--json", action="store_true",
                        help="輸出 JSON 而非 markdown")
    parser.add_argument("--timeout", type=int, default=15,
                        help="URL request timeout（秒）")
    parser.add_argument("--no-verify-ssl", action="store_true",
                        help="不驗 SSL 憑證（避政府網站 SSL chain 問題）")
    args = parser.parse_args()

    print(f"=== probe_textbooks.py ===")
    print(f"探勘 {len(SOURCES)} 個 URL...\n")

    results = []
    for stage, domain, url, source_type, note in SOURCES:
        print(f"  [{stage}/{domain}] {url} ...", end=" ", flush=True)
        r = probe_url(url, timeout=args.timeout, no_verify_ssl=args.no_verify_ssl)
        r["stage"] = stage
        r["domain"] = domain
        r["source_type"] = source_type
        r["note"] = note

        if args.headed:
            text = fetch_first_n_kb(url, max_kb=50, timeout=args.timeout, no_verify_ssl=args.no_verify_ssl)
            r["keywords"] = detect_textbook_keywords(text or "")
        else:
            r["keywords"] = {}

        results.append(r)

        status = r["status"] or "ERR"
        kw_hits = sum(r["keywords"].values()) if r["keywords"] else 0
        kw_str = f" kw={kw_hits}" if args.headed else ""
        print(f"status={status}{kw_str} err={r['error']}")

    now = datetime.now(TZ).isoformat(timespec="seconds")
    out_path = PLANS / f"P2-probe-results-{now[:10]}.md"

    # 寫 markdown 報告
    lines = [
        f"# P2 部編本覆蓋率探勘結果",
        f"",
        f"> 產生時間：{now}",
        f"> 工具：`scripts/probe_textbooks.py`",
        f"> 探勘範圍：{len(results)} 個 URL",
        f"> 模式：{'headed（GET + 關鍵字）' if args.headed else 'head-only（只驗可達）'}",
        f"",
        f"## 結果總覽",
        f"",
        f"| 階段 | 領域 | 來源類型 | URL | HTTP | 內容類型 | 錯誤 | 備註 |",
        f"|------|------|---------|-----|------|---------|------|------|",
    ]
    for r in results:
        kw_str = ""
        if r["keywords"]:
            kw_str = " kw=" + ",".join(f"{k}×{v}" for k, v in r["keywords"].items())
        lines.append(
            f"| {r['stage']} | {r['domain']} | {r['source_type']} | "
            f"<{r['url']}> | {r['status'] or 'ERR'} | "
            f"`{r['content_type'][:40]}` | {r['error'] or '—'} | {r['note']}{kw_str} |"
        )

    lines.extend([
        "",
        "## 解讀",
        "",
        "- **status=200** + 已知 URL：可直接訪問",
        "- **status=200** + kw=0：可達但首頁沒明確部編本 / 課綱關鍵字，需深入點進去看",
        "- **status=301/302**：可達但可能永久或暫時搬遷，需追最終 URL",
        "- **status=4xx/5xx 或 ERR**：不可達，可能是 URL 失效（參考 CLAUDE.md §0 已失效 URL 表）",
        "",
        "## 已知資訊（背景）",
        "",
        "108 課綱（2019 實施）後，教科書政策轉為：",
        "- **部編本 → 審定版**：多數領域（自然科學、社會、藝術、科技、綜合活動、健康與體育、國防、英語文、本土語文）已委由民間出版社編寫，**教育部不再出部編本**",
        "- **仍維持部編本**：國語文（國小 / 國中）、數學（國小 / 國中 / 高中）",
        "- **高中自然科學**：部編本仍存在但逐年過渡到審定版",
        "",
        "**以上是公開資訊的概略結論**。本探勘腳本不下載內容做最終確認，需人工查證。",
        "",
        "## 下一步",
        "",
        "1. user 看這份報告，補上 SOURCES 清單（哪些 NAER PageSyllabus?fid=XX 對應各領域各階段）",
        "2. 針對「可能有部編本」的 URL 加深探勘（跑 --headed，看書目頁內容）",
        "3. 整理出最終「哪些階段哪些領域有合法部編本純文字源」的清單",
        "4. 依結果決定 `textbooks/` 目錄結構（保留現在的國小/國中/高中/<grade>/ 還是改為按來源切）",
        "",
        f"*由 probe_textbooks.py 自動產生於 {now}*",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n結果寫到：{out_path.relative_to(ROOT)}")

    if args.json:
        json_path = PLANS / f"P2-probe-results-{now[:10]}.json"
        json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON 也寫到：{json_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
