#!/usr/bin/env python3
"""
generate_graph.py — P3 知識圖譜 generator。

從 curriculum/<domain>/*.structured.json 產出：
- knowledge-graph/<domain>/graph.json   (nodes + edges)
- knowledge-graph/<domain>/graph.mermaid (視覺化)
- knowledge-graph/<domain>/README.md    (給人讀)
- knowledge-graph/_all-graph.json        (跨領域聚合)
- knowledge-graph/_schema.json           (schema 規格)

設計原則：
- stdlib only（不依賴外部套件）
- idempotent（可重跑，結果一致）
- 從 structured.json 直接讀，不重 parse markdown
- 自動偵測 edges（同 domain + 同 category + 同 ordinal + 跨 stage → prerequisite）
- 人工 edges 可從 plans/<domain>/edges.md 覆寫（如果存在）
- 結構符合 docs/knowledge-graph-schema.md §2 / §3

使用：
    python3 scripts/generate_graph.py              # 跑全部 11 領域 + 聚合
    python3 scripts/generate_graph.py --domain 數學  # 只跑單一領域
    python3 scripts/generate_graph.py --no-write   # 只印統計
    python3 scripts/generate_graph.py --self-test  # 跑 fixture 驗證工具本身沒壞
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
CURRICULUM = ROOT / "curriculum"
PLANS = ROOT / "plans"
KG = ROOT / "knowledge-graph"

SCHEMA_VERSION = "1.0"
STAGE_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


# ───────────────────────────── 讀 curriculum ─────────────────────────────


def load_structured_files(domain: str) -> list[dict]:
    """讀 curriculum/<domain>/*.structured.json，回傳 list of structured dicts。"""
    domain_dir = CURRICULUM / domain
    if not domain_dir.is_dir():
        return []
    files = sorted(domain_dir.glob("*.structured.json"))
    out = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            data["_source_path"] = str(f.relative_to(ROOT))
            out.append(data)
    return out


def all_domains() -> list[str]:
    """列舉 curriculum/ 下所有領域目錄（排除 _index.* 與非目錄）。"""
    out = []
    for d in sorted(CURRICULUM.iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            out.append(d.name)
    return out


# ───────────────────────────── nodes ─────────────────────────────


def build_nodes(domain: str, structured_files: list[dict]) -> tuple[list[dict], list[str]]:
    """從多個 structured.json 抽出所有 nodes + warnings list。"""
    nodes = []
    warnings = []
    for sf in structured_files:
        source_file = sf["_source_path"]
        # content nodes
        for idx, c in enumerate(sf.get("content_codes", [])):
            node = {
                "id": f"{domain}/{c['code']}",
                "domain": domain,
                "code": c["code"],
                "code_format": c.get("code_format", "roman_phase"),
                "stage": c.get("stage", ""),
                "category": c.get("category", ""),
                "ordinal": c.get("ordinal", 0),
                "type": "content",
                "title": "",
                "description": "",
                "source_file": source_file,
                "source_ref": {"structured_section": "content_codes", "index": idx},
                "keywords": [],
                "warnings": [],
            }
            nodes.append(node)
        # performance nodes
        for idx, p in enumerate(sf.get("performance_codes", [])):
            node = {
                "id": f"{domain}/{p['code']}",
                "domain": domain,
                "code": p["code"],
                "code_format": p.get("code_format", "roman_phase"),
                "stage": p.get("stage", ""),
                "category": p.get("category", ""),
                "ordinal": p.get("ordinal", 0),
                "type": "performance",
                "title": "",
                "description": "",
                "source_file": source_file,
                "source_ref": {"structured_section": "performance_codes", "index": idx},
                "keywords": [],
                "warnings": [],
            }
            nodes.append(node)
    return nodes, warnings


# ───────────────────────────── edges 自動偵測 ─────────────────────────────


def auto_detect_stage_monotonic_edges(nodes: list[dict]) -> list[dict]:
    """自動偵測：同 domain + 同 category + 同 ordinal + 跨 stage → prerequisite。

    規則：stage 升序且 ordinal 相同的兩個 node 之間，從前 stage 連到後 stage。
    例如 數學/N-1-1 → 數學/N-2-1 → 數學/N-3-1 → 數學/N-4-1 → 數學/N-5-1。

    注意：這只是「跨 stage 升序」的預設邊，不一定是真實語意前備。
    特殊依賴（跨 ordinal 的非單調依賴）需人工寫 plans/<domain>/edges.md。
    """
    # group: (domain, category, ordinal) → [(stage, node)]
    groups: dict[tuple[str, str, int], list[tuple[str, dict]]] = defaultdict(list)
    for n in nodes:
        groups[(n["domain"], n["category"], n["ordinal"])].append(
            (n.get("stage", ""), n)
        )

    edges = []
    for key, lst in groups.items():
        lst.sort(key=lambda x: STAGE_ORDER.get(x[0], 99))
        # 連續：從 stage_I → stage_II → ... 逐個連
        for i in range(len(lst) - 1):
            a_stage, a_node = lst[i]
            b_stage, b_node = lst[i + 1]
            if (
                a_stage in STAGE_ORDER
                and b_stage in STAGE_ORDER
                and STAGE_ORDER[a_stage] < STAGE_ORDER[b_stage]
            ):
                edges.append({
                    "from": a_node["id"],
                    "to": b_node["id"],
                    "relation": "prerequisite",
                    "strength": "recommended",
                    "note": "auto-detected: stage-monotonic same-ordinal",
                    "source": "auto",
                })
    return edges


def load_manual_edges(domain: str) -> list[dict]:
    """從 plans/<domain>/edges.md 讀人工標註的邊。

    格式（每行一條）：
        from_code to_code [strength] [note]

    例：
        數學/N-3-3 數學/N-3-4 required 分數比較需先有分數概念
        數學/N-3-3 數學/N-3-5 required 分數比較也用於分數應用
    """
    edges_file = PLANS / domain / "edges.md"
    if not edges_file.is_file():
        return []
    out = []
    text = edges_file.read_text(encoding="utf-8")
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            print(f"  WARN {edges_file}:{line_no} 格式錯誤（至少要 from to）", file=sys.stderr)
            continue
        from_code, to_code = parts[0], parts[1]
        strength = parts[2] if len(parts) >= 3 else "recommended"
        note = " ".join(parts[3:]) if len(parts) >= 4 else ""
        out.append({
            "from": f"{domain}/{from_code}",
            "to": f"{domain}/{to_code}",
            "relation": "prerequisite",
            "strength": strength,
            "note": note,
            "source": f"manual:{edges_file.relative_to(ROOT)}",
        })
    return out


# ───────────────────────────── mermaid 產出 ─────────────────────────────


def to_mermaid_id(code: str) -> str:
    """Mermaid 不支援 / 跟 - 在節點 id，用 _ 取代。"""
    return code.replace("/", "_").replace("-", "_")


def to_mermaid(nodes: list[dict], edges: list[dict]) -> str:
    """產 Mermaid graph LR 字串。"""
    lines = ["graph LR"]
    # 節點宣告（去重）
    seen = set()
    for n in nodes:
        mid = to_mermaid_id(n["id"])
        if mid in seen:
            continue
        seen.add(mid)
        label = f"{n['id']}<br/>({n.get('stage', '?')}/{n.get('type', '?')})"
        # Mermaid 節點 label 用 ["..."] 包起來，內容 <br/> 換行
        lines.append(f'  {mid}["{label}"]')
    # 邊
    for e in edges:
        from_id = to_mermaid_id(e["from"])
        to_id = to_mermaid_id(e["to"])
        rel = e.get("relation", "prerequisite")
        lines.append(f"  {from_id} -->|{rel}| {to_id}")
    return "\n".join(lines) + "\n"


# ───────────────────────────── README 產出 ─────────────────────────────


def to_readme(domain: str, nodes: list[dict], edges: list[dict], structured_files: list[dict]) -> str:
    """產該領域的 README.md（給人讀的領域圖譜說明）。"""
    perf_n = sum(1 for n in nodes if n["type"] == "performance")
    cont_n = sum(1 for n in nodes if n["type"] == "content")
    stage_count = defaultdict(int)
    cat_count = defaultdict(int)
    for n in nodes:
        stage_count[n.get("stage", "?")] += 1
        cat_count[n.get("category", "?")] += 1

    source_files = sorted({sf["_source_path"] for sf in structured_files})
    auto_edges = sum(1 for e in edges if e.get("source") == "auto")
    manual_edges = sum(1 for e in edges if e.get("source", "").startswith("manual"))

    lines = [
        f"# {domain} — 知識圖譜",
        "",
        f"> 自動產生於 {datetime.now(TZ).isoformat(timespec='seconds')}",
        f"> 工具：`scripts/generate_graph.py`",
        f"> 來源 schema：`docs/knowledge-graph-schema.md`",
        "",
        "## 統計",
        "",
        f"- **總 nodes**：{len(nodes)}（content {cont_n} + performance {perf_n}）",
        f"- **總 edges**：{len(edges)}（auto-detect {auto_edges} + manual {manual_edges}）",
        f"- **來源 .structured.json**：{len(source_files)} 個",
        "",
        "### 各 stage 分布",
        "",
        "| Stage | 數量 |",
        "|-------|------|",
    ]
    for stage in sorted(stage_count.keys(), key=lambda s: STAGE_ORDER.get(s, 99)):
        lines.append(f"| {stage} | {stage_count[stage]} |")

    lines.extend([
        "",
        "### 各 category 分布（取前 10）",
        "",
        "| Category | 數量 |",
        "|----------|------|",
    ])
    for cat, cnt in sorted(cat_count.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"| {cat} | {cnt} |")

    lines.extend([
        "",
        "## 檔案",
        "",
        "- `graph.json` — 完整 nodes + edges",
        "- `graph.mermaid` — Mermaid 視覺化（> 50 nodes 圖會擠，可到 https://mermaid.live 渲染）",
        "- 本 README — 給人看的領域摘要",
        "",
        "## 如何讀這個圖譜",
        "",
        "- `node.id` 格式：`<domain>/<code>`，例如 `數學/N-3-1`",
        "- `node.type`：`content`（學習內容）/ `performance`（學習表現）",
        "- `edge.from → edge.to`：學完 from 才能學 to（from 是 to 的前備）",
        "- `edge.strength`：`required` / `recommended` / `optional`",
        "- `edge.source`：`auto`（自動偵測）或 `manual:<file>`（人工標註）",
        "",
        "## 邊的來源",
        "",
        f"- **auto-detect**：同 category + 同 ordinal + 跨 stage 升序（推薦起點，不一定語意正確）",
        f"- **manual**：{PLANS.name}/{domain}/edges.md（如有）",
        "",
        "## 下一步",
        "",
        "- 加 `plans/<domain>/edges.md` 補特殊依賴（auto-detect 不夠時）",
        "- 從 `raw_section_5` 自動抽取 `node.title` / `node.description`（heuristic）",
        "- 跨 domain 邊（v2 才做）",
        "",
        f"*由 generate_graph.py 自動產生於 {datetime.now(TZ).isoformat(timespec='seconds')}*",
    ])
    return "\n".join(lines) + "\n"


# ───────────────────────────── 主流程 ─────────────────────────────


def build_domain_graph(domain: str) -> dict:
    """產單一領域的 graph dict（nodes + edges + meta）。"""
    sfs = load_structured_files(domain)
    nodes, _ = build_nodes(domain, sfs)
    auto_edges = auto_detect_stage_monotonic_edges(nodes)
    manual_edges = load_manual_edges(domain)
    edges = auto_edges + manual_edges

    # dedupe edge（防 manual 重複加 auto）
    seen_edges = set()
    deduped = []
    for e in edges:
        key = (e["from"], e["to"], e["relation"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        deduped.append(e)
    edges = deduped

    return {
        "schema_version": SCHEMA_VERSION,
        "domain": domain,
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "structure_types": sorted({sf.get("structure_type", "?") for sf in sfs}),
        "stages_present": sorted(
            {n.get("stage", "") for n in nodes if n.get("stage")},
            key=lambda s: STAGE_ORDER.get(s, 99),
        ),
        "source_files": sorted({sf["_source_path"] for sf in sfs}),
        "nodes": nodes,
        "edges": edges,
    }


def write_domain_graph(domain: str, g: dict, write: bool = True) -> dict:
    """寫該領域的 graph.json / graph.mermaid / README.md。"""
    domain_dir = KG / domain
    if write:
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / "graph.json").write_text(
            json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Mermaid
        mermaid = to_mermaid(g["nodes"], g["edges"])
        (domain_dir / "graph.mermaid").write_text(mermaid, encoding="utf-8")
        # README
        # 需要 structured_files 重新載入（build_domain_graph 內已丟掉）— 從 graph 內 source_files 反查
        sfs = []
        for src in g.get("source_files", []):
            f = ROOT / src
            if f.is_file():
                with open(f, encoding="utf-8") as fp:
                    d = json.load(fp)
                    d["_source_path"] = src
                    sfs.append(d)
        readme = to_readme(domain, g["nodes"], g["edges"], sfs)
        (domain_dir / "README.md").write_text(readme, encoding="utf-8")
    return {
        "domain": domain,
        "nodes": g["total_nodes"],
        "edges": g["total_edges"],
        "stages": g["stages_present"],
    }


def build_all_graph(domains: list[str]) -> dict:
    """產跨領域聚合 _all-graph.json。"""
    all_nodes = []
    all_edges = []
    domain_summary = []
    for d in domains:
        g = build_domain_graph(d)
        all_nodes.extend(g["nodes"])
        all_edges.extend(g["edges"])
        domain_summary.append({
            "domain": d,
            "nodes": g["total_nodes"],
            "edges": g["total_edges"],
            "stages": g["stages_present"],
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "domains": domains,
        "total_nodes": len(all_nodes),
        "total_edges": len(all_edges),
        "by_domain": domain_summary,
        "nodes": all_nodes,
        "edges": all_edges,
    }


def write_all_graph(domains: list[str], write: bool = True) -> dict:
    g = build_all_graph(domains)
    if write:
        KG.mkdir(parents=True, exist_ok=True)
        (KG / "_all-graph.json").write_text(
            json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {
        "total_nodes": g["total_nodes"],
        "total_edges": g["total_edges"],
        "domains": g["by_domain"],
    }


SCHEMA_SPEC = {
    "schema_version": SCHEMA_VERSION,
    "description": "P3 知識圖譜 schema 規格（對應 docs/knowledge-graph-schema.md）",
    "node": {
        "required": ["id", "domain", "code", "code_format", "stage", "category", "ordinal", "type", "source_file"],
        "optional": ["title", "description", "source_ref", "keywords", "warnings"],
        "fields": {
            "id": "格式 <domain>/<code>，唯一",
            "domain": "11 領域名（中文）+ 總綱",
            "code": "原始 curriculum 編碼",
            "code_format": "numeric_phase 或 roman_phase",
            "stage": "I/II/III/IV/V",
            "category": "編碼前綴",
            "ordinal": "序號 int",
            "type": "content 或 performance",
            "title": "v1 留空（TODO 從 raw_section_5 抽取）",
            "description": "v1 留空",
            "source_file": "對應 structured.json 路徑",
            "source_ref": "指向 structured.json 內位置",
            "keywords": "v1 留空（跨域搜尋用）",
            "warnings": "非阻擋問題",
        },
    },
    "edge": {
        "required": ["from", "to", "relation"],
        "optional": ["strength", "note", "source"],
        "fields": {
            "from": "來源節點 id（前備）",
            "to": "目標節點 id（後學）",
            "relation": "prerequisite / related / extends",
            "strength": "required / recommended / optional",
            "note": "一句話說明",
            "source": "auto / manual:<file>",
        },
    },
    "domain_graph": {
        "required": ["schema_version", "domain", "total_nodes", "total_edges", "nodes", "edges"],
    },
    "all_graph": {
        "required": ["schema_version", "domains", "total_nodes", "total_edges", "by_domain", "nodes", "edges"],
    },
}


def write_schema(write: bool = True) -> None:
    if write:
        KG.mkdir(parents=True, exist_ok=True)
        (KG / "_schema.json").write_text(
            json.dumps(SCHEMA_SPEC, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ───────────────────────────── self-test ─────────────────────────────


SELF_TEST_NODES = [
    {"id": "TEST/A-1-1", "domain": "TEST", "code": "A-1-1", "code_format": "numeric_phase",
     "stage": "I", "category": "A", "ordinal": 1, "type": "content",
     "title": "", "description": "", "source_file": "test.json",
     "source_ref": {}, "keywords": [], "warnings": []},
    {"id": "TEST/A-2-1", "domain": "TEST", "code": "A-2-1", "code_format": "numeric_phase",
     "stage": "II", "category": "A", "ordinal": 1, "type": "content",
     "title": "", "description": "", "source_file": "test.json",
     "source_ref": {}, "keywords": [], "warnings": []},
    {"id": "TEST/A-3-1", "domain": "TEST", "code": "A-3-1", "code_format": "numeric_phase",
     "stage": "III", "category": "A", "ordinal": 1, "type": "content",
     "title": "", "description": "", "source_file": "test.json",
     "source_ref": {}, "keywords": [], "warnings": []},
    {"id": "TEST/B-1-1", "domain": "TEST", "code": "B-1-1", "code_format": "numeric_phase",
     "stage": "I", "category": "B", "ordinal": 1, "type": "performance",
     "title": "", "description": "", "source_file": "test.json",
     "source_ref": {}, "keywords": [], "warnings": []},
    {"id": "TEST/C-2-5", "domain": "TEST", "code": "C-2-5", "code_format": "numeric_phase",
     "stage": "II", "category": "C", "ordinal": 5, "type": "content",
     "title": "", "description": "", "source_file": "test.json",
     "source_ref": {}, "keywords": [], "warnings": []},
]


def self_test() -> int:
    """跑 fixture 驗證 generator 本身沒壞。失敗 exit 2。"""
    print("=== generate_graph.py self-test ===")
    fail = 0

    # Test 1: auto_detect_stage_monotonic_edges 應產 2 條（A-1-1→A-2-1→A-3-1）
    edges = auto_detect_stage_monotonic_edges(SELF_TEST_NODES)
    expected = 2
    if len(edges) == expected:
        print(f"  [PASS] auto_detect stage-monotonic → {len(edges)} edges (expected {expected})")
    else:
        print(f"  [FAIL] auto_detect → {len(edges)} edges (expected {expected})")
        fail += 1

    # Test 2: 邊的 from/to 都對應到 node id
    node_ids = {n["id"] for n in SELF_TEST_NODES}
    for e in edges:
        if e["from"] not in node_ids or e["to"] not in node_ids:
            print(f"  [FAIL] edge 起終點不存在: {e}")
            fail += 1
    if all(e["from"] in node_ids and e["to"] in node_ids for e in edges):
        print(f"  [PASS] 所有 edge 起終點都對應到 node id")

    # Test 3: stage 升序 (from.stage < to.stage)
    by_id = {n["id"]: n for n in SELF_TEST_NODES}
    for e in edges:
        fs = by_id[e["from"]].get("stage", "")
        ts = by_id[e["to"]].get("stage", "")
        if STAGE_ORDER.get(fs, 0) >= STAGE_ORDER.get(ts, 99):
            print(f"  [FAIL] edge 違反 stage 升序: {e['from']}({fs}) → {e['to']}({ts})")
            fail += 1
    if all(STAGE_ORDER.get(by_id[e["from"]].get("stage", ""), 0) < STAGE_ORDER.get(by_id[e["to"]].get("stage", ""), 99) for e in edges):
        print(f"  [PASS] 所有 edge 都 stage 升序")

    # Test 4: mermaid 產出格式正確
    md = to_mermaid(SELF_TEST_NODES, edges)
    if md.startswith("graph LR\n") and "A_1_1" in md and "-->|prerequisite|" in md:
        print(f"  [PASS] mermaid 產出格式正確（{len(md)} chars）")
    else:
        print(f"  [FAIL] mermaid 產出格式錯：\n{md}")
        fail += 1

    # Test 5: load_manual_edges 不存在檔應回 []
    e = load_manual_edges("不存在的領域xyz")
    if e == []:
        print(f"  [PASS] load_manual_edges 不存在檔 → []")
    else:
        print(f"  [FAIL] load_manual_edges → {e}")
        fail += 1

    if fail:
        print(f"\n=== self-test FAILED ({fail} 項) ===")
        return 2
    print(f"\n=== self-test PASS (5/5) ===")
    return 0


# ───────────────────────────── main ─────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="P3 知識圖譜 generator")
    parser.add_argument("--domain", help="只跑單一領域")
    parser.add_argument("--no-write", action="store_true", help="不寫檔，只印統計")
    parser.add_argument("--self-test", action="store_true", help="跑 self-test")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if args.domain:
        domains = [args.domain]
    else:
        domains = all_domains()

    write = not args.no_write
    print(f"=== generate_graph.py ===")
    print(f"目標：{len(domains)} 個領域")
    if args.no_write:
        print("模式：dry-run（不寫檔）")
    print()

    summary = []
    for d in domains:
        g = build_domain_graph(d)
        info = write_domain_graph(d, g, write=write)
        summary.append(info)
        print(
            f"  [{d:>8}] nodes={info['nodes']:>4}  edges={info['edges']:>4}  "
            f"stages={'/'.join(info['stages']) or '(none)':<12}"
        )

    # _all-graph.json + _schema.json
    all_info = write_all_graph(domains, write=write)
    write_schema(write=write)

    print()
    print(f"=== 總計 ===")
    print(f"  total nodes: {all_info['total_nodes']}")
    print(f"  total edges: {all_info['total_edges']}")
    print(f"  domains: {len(domains)}")

    if write:
        print(f"\n  寫到：")
        print(f"    knowledge-graph/_all-graph.json")
        print(f"    knowledge-graph/_schema.json")
        for d in domains:
            print(f"    knowledge-graph/{d}/graph.json")
            print(f"    knowledge-graph/{d}/graph.mermaid")
            print(f"    knowledge-graph/{d}/README.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())