#!/usr/bin/env python3
"""
verify_graph.py — P3 知識圖譜驗證腳本。

對應 docs/knowledge-graph-schema.md §12 驗證方法，跑 6 項檢查：
1. node 數量一致：graph.total_nodes = perf + content 個
2. edge 起終點存在：所有 from/to 都對應到 graph 內 node
3. 無循環：prerequisite 邊不形成 cycle
4. stage 單調：auto-detected edge 的 from.stage < to.stage
5. schema 合規：每個 node/edge 符合 schema 必填欄位
6. 跨 domain 聚合一致：_all-graph.json 的 nodes = 各 domain nodes 聯集（無重複）

回傳 exit code：
- 0：全綠
- 1：資料壞（驗證失敗）
- 2：工具壞（self-test 失敗）

使用：
    python3 scripts/verify_graph.py              # 驗證所有 11 領域 + _all
    python3 scripts/verify_graph.py --domain 數學 # 只驗單一領域
    python3 scripts/verify_graph.py --self-test   # 跑 fixture 驗證工具本身
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent
KG = ROOT / "knowledge-graph"

STAGE_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


# ───────────────────────────── 檢查邏輯 ─────────────────────────────


REQUIRED_NODE_FIELDS = {"id", "domain", "code", "code_format", "stage", "category", "ordinal", "type", "source_file"}
REQUIRED_EDGE_FIELDS = {"from", "to", "relation"}


def check_node_counts(g: dict) -> list[str]:
    """1. graph.total_nodes = perf + content 個。"""
    errors = []
    declared = g.get("total_nodes", 0)
    actual = len(g.get("nodes", []))
    if declared != actual:
        errors.append(f"  total_nodes={declared} 但 nodes 實際數={actual}")
    return errors


def check_edges_reference_existing_nodes(g: dict) -> list[str]:
    """2. 所有 edge from/to 都對應到 graph 內的 node。"""
    errors = []
    node_ids = {n["id"] for n in g.get("nodes", [])}
    for i, e in enumerate(g.get("edges", [])):
        if e["from"] not in node_ids:
            errors.append(f"  edge[{i}] from={e['from']} 找不到對應 node")
        if e["to"] not in node_ids:
            errors.append(f"  edge[{i}] to={e['to']} 找不到對應 node")
    return errors


def check_no_cycles(g: dict) -> list[str]:
    """3. prerequisite 邊不形成 cycle（DFS 偵測）。"""
    errors = []
    adj: dict[str, list[str]] = defaultdict(list)
    for e in g.get("edges", []):
        if e.get("relation") == "prerequisite":
            adj[e["from"]].append(e["to"])

    # DFS 三色標記
    WHITE, GRAY, BLACK = 0, 1, 2
    color = defaultdict(int)  # default WHITE

    def dfs(u: str) -> bool:
        """回傳 True 表示有 cycle。"""
        color[u] = GRAY
        for v in adj[u]:
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for u in list(adj.keys()):
        if color[u] == WHITE and dfs(u):
            errors.append(f"  偵測到 cycle（從 {u} 出發）")
            break
    return errors


def check_stage_monotonic(g: dict) -> list[str]:
    """4. auto-detected edge 的 from.stage < to.stage（手動邊跳過）。"""
    errors = []
    by_id = {n["id"]: n for n in g.get("nodes", [])}
    for i, e in enumerate(g.get("edges", [])):
        if not (e.get("source", "").startswith("auto") or e.get("source") == "auto"):
            continue
        from_stage = by_id.get(e["from"], {}).get("stage", "")
        to_stage = by_id.get(e["to"], {}).get("stage", "")
        if from_stage not in STAGE_ORDER or to_stage not in STAGE_ORDER:
            errors.append(f"  auto edge[{i}] {e['from']}({from_stage}) → {e['to']}({to_stage}) stage 不在 I-V")
            continue
        if STAGE_ORDER[from_stage] >= STAGE_ORDER[to_stage]:
            errors.append(f"  auto edge[{i}] {e['from']}({from_stage}) → {e['to']}({to_stage}) 違反 stage 升序")
    return errors


def check_schema(g: dict) -> list[str]:
    """5. 每個 node/edge 符合 schema 必填欄位。"""
    errors = []
    for i, n in enumerate(g.get("nodes", [])):
        missing = REQUIRED_NODE_FIELDS - set(n.keys())
        if missing:
            errors.append(f"  node[{i}] {n.get('id', '?')} 缺欄位: {missing}")
    for i, e in enumerate(g.get("edges", [])):
        missing = REQUIRED_EDGE_FIELDS - set(e.keys())
        if missing:
            errors.append(f"  edge[{i}] {e.get('from', '?')} → {e.get('to', '?')} 缺欄位: {missing}")
    return errors


def check_all_graph_consistency(all_g: dict, domain_gs: dict[str, dict]) -> list[str]:
    """6. _all-graph.json nodes = 各 domain nodes 聯集（無重複，無缺漏）。"""
    errors = []
    all_node_ids = {n["id"] for n in all_g.get("nodes", [])}
    domain_node_ids = set()
    for d, g in domain_gs.items():
        for n in g.get("nodes", []):
            domain_node_ids.add(n["id"])

    missing_in_all = domain_node_ids - all_node_ids
    extra_in_all = all_node_ids - domain_node_ids
    if missing_in_all:
        errors.append(f"  _all-graph 漏了 {len(missing_in_all)} 個 node，例如：{list(missing_in_all)[:3]}")
    if extra_in_all:
        errors.append(f"  _all-graph 多了 {len(extra_in_all)} 個 node，例如：{list(extra_in_all)[:3]}")

    # 邊也是
    all_edge_set = {(e["from"], e["to"], e["relation"]) for e in all_g.get("edges", [])}
    domain_edge_set = set()
    for d, g in domain_gs.items():
        for e in g.get("edges", []):
            domain_edge_set.add((e["from"], e["to"], e["relation"]))

    missing_edges = domain_edge_set - all_edge_set
    extra_edges = all_edge_set - domain_edge_set
    if missing_edges:
        errors.append(f"  _all-graph 漏了 {len(missing_edges)} 條邊，例如：{list(missing_edges)[:3]}")
    if extra_edges:
        errors.append(f"  _all-graph 多了 {len(extra_edges)} 條邊，例如：{list(extra_edges)[:3]}")

    return errors


def verify_domain(g: dict) -> list[str]:
    """對單一 domain graph 跑檢查 1-5。"""
    errors = []
    errors.extend([f"[{g['domain']}] " + e for e in check_node_counts(g)])
    errors.extend([f"[{g['domain']}] " + e for e in check_edges_reference_existing_nodes(g)])
    errors.extend([f"[{g['domain']}] " + e for e in check_no_cycles(g)])
    errors.extend([f"[{g['domain']}] " + e for e in check_stage_monotonic(g)])
    errors.extend([f"[{g['domain']}] " + e for e in check_schema(g)])
    return errors


# ───────────────────────────── self-test ─────────────────────────────


def self_test() -> int:
    """跑 fixture 驗證 verify_graph 工具本身沒壞。"""
    print("=== verify_graph.py self-test ===")
    fail = 0

    # Fixture 1: 完美的 graph
    good_g = {
        "domain": "TEST",
        "total_nodes": 3,
        "nodes": [
            {"id": "T/A-1-1", "domain": "T", "code": "A-1-1", "code_format": "numeric_phase",
             "stage": "I", "category": "A", "ordinal": 1, "type": "content", "source_file": "t.json"},
            {"id": "T/A-2-1", "domain": "T", "code": "A-2-1", "code_format": "numeric_phase",
             "stage": "II", "category": "A", "ordinal": 1, "type": "content", "source_file": "t.json"},
            {"id": "T/A-3-1", "domain": "T", "code": "A-3-1", "code_format": "numeric_phase",
             "stage": "III", "category": "A", "ordinal": 1, "type": "content", "source_file": "t.json"},
        ],
        "edges": [
            {"from": "T/A-1-1", "to": "T/A-2-1", "relation": "prerequisite", "source": "auto"},
            {"from": "T/A-2-1", "to": "T/A-3-1", "relation": "prerequisite", "source": "auto"},
        ],
    }
    errs = verify_domain(good_g)
    if not errs:
        print(f"  [PASS] good_g 全綠")
    else:
        print(f"  [FAIL] good_g 應全綠但有 {len(errs)} 錯：\n    " + "\n    ".join(errs))
        fail += 1

    # Fixture 2: node 數不一致
    bad_count = dict(good_g)
    bad_count["total_nodes"] = 999
    errs = verify_domain(bad_count)
    if any("total_nodes" in e for e in errs):
        print(f"  [PASS] bad_count 抓到 total_nodes 不一致")
    else:
        print(f"  [FAIL] bad_count 應抓到不一致")
        fail += 1

    # Fixture 3: edge 找不到 node
    bad_edge = dict(good_g)
    bad_edge["edges"] = [{"from": "T/NONEXIST", "to": "T/A-1-1", "relation": "prerequisite"}]
    errs = verify_domain(bad_edge)
    if any("NONEXIST" in e for e in errs):
        print(f"  [PASS] bad_edge 抓到 edge from 找不到 node")
    else:
        print(f"  [FAIL] bad_edge 應抓不到 node")
        fail += 1

    # Fixture 4: cycle (A→B→A)
    cycle_g = {
        "domain": "CYCLE",
        "total_nodes": 2,
        "nodes": [
            {"id": "C/A-1", "domain": "C", "code": "A-1", "code_format": "numeric_phase",
             "stage": "I", "category": "A", "ordinal": 1, "type": "content", "source_file": "c.json"},
            {"id": "C/A-2", "domain": "C", "code": "A-2", "code_format": "numeric_phase",
             "stage": "II", "category": "A", "ordinal": 1, "type": "content", "source_file": "c.json"},
        ],
        "edges": [
            {"from": "C/A-1", "to": "C/A-2", "relation": "prerequisite"},
            {"from": "C/A-2", "to": "C/A-1", "relation": "prerequisite"},
        ],
    }
    errs = verify_domain(cycle_g)
    if any("cycle" in e for e in errs):
        print(f"  [PASS] cycle_g 抓到 cycle")
    else:
        print(f"  [FAIL] cycle_g 應抓到 cycle")
        fail += 1

    # Fixture 5: stage 不升序
    bad_stage = {
        "domain": "STAGE",
        "total_nodes": 2,
        "nodes": [
            {"id": "S/A-3", "domain": "S", "code": "A-3", "code_format": "numeric_phase",
             "stage": "III", "category": "A", "ordinal": 1, "type": "content", "source_file": "s.json"},
            {"id": "S/A-1", "domain": "S", "code": "A-1", "code_format": "numeric_phase",
             "stage": "I", "category": "A", "ordinal": 1, "type": "content", "source_file": "s.json"},
        ],
        "edges": [
            {"from": "S/A-3", "to": "S/A-1", "relation": "prerequisite", "source": "auto"},
        ],
    }
    errs = verify_domain(bad_stage)
    if any("stage 升序" in e for e in errs):
        print(f"  [PASS] bad_stage 抓到 stage 不升序")
    else:
        print(f"  [FAIL] bad_stage 應抓 stage 不升序")
        fail += 1

    # Fixture 6: schema 缺欄位
    bad_schema = {
        "domain": "SCHEMA",
        "total_nodes": 1,
        "nodes": [
            {"id": "M/A-1", "domain": "M"},  # 缺一堆欄位
        ],
        "edges": [],
    }
    errs = verify_domain(bad_schema)
    if any("缺欄位" in e for e in errs):
        print(f"  [PASS] bad_schema 抓到缺欄位")
    else:
        print(f"  [FAIL] bad_schema 應抓缺欄位")
        fail += 1

    if fail:
        print(f"\n=== self-test FAILED ({fail} 項) ===")
        return 2
    print(f"\n=== self-test PASS (6/6) ===")
    return 0


# ───────────────────────────── main ─────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="P3 知識圖譜驗證")
    parser.add_argument("--domain", help="只驗單一領域")
    parser.add_argument("--self-test", action="store_true", help="跑 self-test")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not KG.is_dir():
        print(f"ERROR: {KG} 不存在，先跑 generate_graph.py")
        return 1

    if args.domain:
        g_path = KG / args.domain / "graph.json"
        if not g_path.is_file():
            print(f"ERROR: {g_path} 不存在")
            return 1
        g = json.loads(g_path.read_text(encoding="utf-8"))
        errs = verify_domain(g)
        if errs:
            print(f"=== {args.domain} 驗證失敗 ===")
            for e in errs:
                print(e)
            return 1
        else:
            print(f"=== {args.domain} PASS ===")
            return 0

    # 全驗
    print(f"=== verify_graph.py ===")
    print(f"驗證時間：{datetime.now(TZ).isoformat(timespec='seconds')}\n")

    domain_gs = {}
    all_errors = []
    summary = []
    for d_dir in sorted(KG.iterdir()):
        if not d_dir.is_dir():
            continue
        if d_dir.name.startswith("_"):
            continue
        g_path = d_dir / "graph.json"
        if not g_path.is_file():
            print(f"  SKIP {d_dir.name}（無 graph.json）")
            continue
        g = json.loads(g_path.read_text(encoding="utf-8"))
        errs = verify_domain(g)
        domain_gs[d_dir.name] = g
        if errs:
            all_errors.extend(errs)
            print(f"  [FAIL] {d_dir.name:>10} nodes={g['total_nodes']:>4} edges={g['total_edges']:>4} — {len(errs)} 錯")
            for e in errs[:5]:
                print(f"         {e}")
            if len(errs) > 5:
                print(f"         ... 還有 {len(errs) - 5} 錯")
        else:
            print(f"  [PASS] {d_dir.name:>10} nodes={g['total_nodes']:>4} edges={g['total_edges']:>4}")
        summary.append((d_dir.name, g["total_nodes"], g["total_edges"], len(errs)))

    # _all-graph.json
    all_path = KG / "_all-graph.json"
    if all_path.is_file():
        all_g = json.loads(all_path.read_text(encoding="utf-8"))
        consistency_errs = check_all_graph_consistency(all_g, domain_gs)
        if consistency_errs:
            all_errors.extend(consistency_errs)
            print(f"\n  [FAIL] _all-graph 一致性 — {len(consistency_errs)} 錯")
            for e in consistency_errs:
                print(f"         {e}")
        else:
            print(f"\n  [PASS] _all-graph 一致性 nodes={all_g['total_nodes']} edges={all_g['total_edges']}")

    # schema check
    schema_path = KG / "_schema.json"
    if schema_path.is_file():
        print(f"  [INFO] _schema.json 存在")

    print(f"\n=== 統計 ===")
    total_nodes = sum(n for _, n, _, _ in summary)
    total_edges = sum(e for _, _, e, _ in summary)
    pass_count = sum(1 for _, _, _, err in summary if err == 0)
    print(f"  domains: {len(summary)}")
    print(f"  total nodes: {total_nodes}")
    print(f"  total edges: {total_edges}")
    print(f"  pass: {pass_count}/{len(summary)}")

    if all_errors:
        print(f"\n=== FAIL ===")
        print(f"總錯誤：{len(all_errors)}")
        return 1
    print(f"\n=== ALL PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())