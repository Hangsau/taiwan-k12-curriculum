#!/usr/bin/env python3
"""
generate_textbooks.py — §15-D：從 curriculum/.structured.json 自動生成教材 .md。

設計：對 5 個均一台沒教材的領域（藝術/健康/綜合/科技/國防），用本腳本生成
「AI 衍生教材」（基於 108 課綱編碼 + 學習重點）。

每個領域 × 每個 stage（II/III/IV/V）產一個 .md，結構：
- 年級簡介（哪個階段、學什麼）
- 章節列表（按 category 分組：例如藝術的 E 視覺/A 音樂/P 表演）
- 每章節對應的 learning content code + 簡短描述（從 raw_section_5 抽或預設）
- 教學目標（從 performance codes 反推）
- 教學活動建議（依 SDT 自主/勝任/關聯）

產出 frontmatter：
- source: "AI-generated based on 108 課綱"
- source_url: "<curriculum/<domain>/...>"
- license: "依 curriculum/ 結構化資料衍生（CC BY 4.0 for the underlying 108 課綱）"
- aligned_codes: 對應的 curriculum codes

Usage:
    python3 scripts/generate_textbooks.py --domain 藝術     # 單一領域
    python3 scripts/generate_textbooks.py --all             # 5 缺漏領域全做
"""
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
TEXTBOOKS = ROOT / "textbooks"

# 5 個均一台沒教材的領域
MISSING_DOMAINS = ["藝術", "健康與體育", "綜合活動", "科技", "國防"]

# 108 課綱 stage 對應學制
STAGE_NAMES = {
    "I": ("國小低年級", "國小 1-2 年級"),
    "II": ("國小中年級", "國小 3-4 年級"),
    "III": ("國小高年級", "國小 5-6 年級"),
    "IV": ("國中", "國中 7-9 年級"),
    "V": ("高中", "高中 10-12 年級"),
}

# 領域簡介（從 108 課綱總體）
DOMAIN_INTRO = {
    "藝術": """藝術領域包含視覺藝術、音樂、表演藝術三項科目。透過參與藝術活動，培養學生藝術感知、創作與鑑賞的能力，同時發展想像力與創造力。本領域強調跨藝術類科的整合學習，讓學生在體驗中感受藝術的美好與意義。""",
    "健康與體育": """健康與體育領域包含健康教育、體育、營養等議題。旨在培養學生健康知識、運動技能與良好生活習慣，促進身心健康發展。""",
    "綜合活動": """綜合活動領域包含童軍、服務學習、家政、生涯發展等。強調實作體驗與生活實踐，培養學生解決問題、團隊合作與自主行動的能力。""",
    "科技": """科技領域包含生活科技與資訊科技。旨在培養學生科技素養，運用科技工具解決問題，進行設計與製作活動。""",
    "國防": """全民國防教育為高中階段的必修科目。旨在培養學生國防知識、捍衛國家安全的意識與素養。""",
}

CATEGORY_DESC = {
    # 藝術
    "E": "視覺藝術（Visual Arts）— 繪畫、設計、雕塑、攝影等視覺創作。",
    "A": "音樂（Music）— 歌唱、樂器演奏、樂理、聆聽等。",
    "P": "表演藝術（Performing Arts）— 戲劇、舞蹈、民俗表演等。",
    # 健康
    "1": "生長、發育與健康",
    "2": "安全生活與運動防護",
    "3": "群體健康與運動參與",
    "4": "飲食與營養",
    "5": "性教育與健康",
    # 綜合
    "a": "童軍活動",
    "b": "服務學習",
    "c": "家政",
    "d": "生涯發展",
    # 科技
    "Aa": "設計與製作的核心概念",
    "Ab": "科技的應用",
    "Ac": "科技與社會",
    # 國防
}


def log(msg: str):
    print(msg, flush=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def slugify(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|\s]+', '_', name.strip())
    return s[:80]


def get_codes_by_stage_cat(structured: dict) -> dict:
    """把 perf + cont codes 按 (stage, category) 分組。"""
    groups = defaultdict(lambda: {"perf": [], "cont": []})
    for c in structured.get("performance_codes", []):
        groups[(c["stage"], c["category"])]["perf"].append(c)
    for c in structured.get("content_codes", []):
        groups[(c["stage"], c["category"])]["cont"].append(c)
    return dict(groups)


def extract_topic_hint(raw: str, code: str) -> str:
    """從 raw_section_5 找 code 附近的中文標題作為簡短描述。"""
    if not raw:
        return ""
    # 找 code 出現位置 + 後續中文 30 字
    pos = raw.find(code)
    if pos < 0:
        return ""
    after = raw[pos + len(code):pos + len(code) + 60]
    # 抓第一個有意義的中文段（去除空白、數字、英文）
    m = re.search(r'[一-鿿][一-鿿、，。：；\s]{4,40}', after)
    if m:
        return m.group(0).strip()[:50]
    return ""


def generate_textbook(domain: str, structured: dict, stage: str, raw_section_5: str) -> str:
    """生成單一 stage 的教材 .md 內容。"""
    stage_label, stage_desc = STAGE_NAMES.get(stage, (stage, stage))
    title = f"{domain}領域 — {stage_desc}"

    md_lines = [
        f"# {title}",
        "",
        f"> **領域**：{domain}",
        f"> **階段**：{stage_desc}（編碼 {stage}）",
        f"> **生成方式**：AI 衍生（基於 108 課綱 + 結構化資料，非均一下載）",
        "",
        "## 領域簡介",
        "",
        DOMAIN_INTRO.get(domain, "本領域..."),
        "",
        "## 編碼分布",
        "",
    ]

    # 編碼分布表
    by_stage = get_codes_by_stage_cat(structured)
    in_stage = {k: v for k, v in by_stage.items() if k[0] == stage}
    md_lines.append(f"本章節涵蓋 {len(in_stage)} 個 category：")
    md_lines.append("")
    md_lines.append("| Category | 學習表現數 | 學習內容數 | 說明 |")
    md_lines.append("|----------|-----------|-----------|------|")
    for (s, cat), codes in sorted(in_stage.items()):
        desc = CATEGORY_DESC.get(cat, "")
        md_lines.append(f"| {cat} | {len(codes['perf'])} | {len(codes['cont'])} | {desc} |")
    md_lines.append("")

    # 學習內容章節
    md_lines.append("## 章節列表")
    md_lines.append("")
    for (s, cat), codes in sorted(in_stage.items()):
        desc = CATEGORY_DESC.get(cat, "")
        md_lines.append(f"### {cat} — {desc}")
        md_lines.append("")
        # 學習內容（content）— 章節本體
        if codes["cont"]:
            md_lines.append("**學習內容**：")
            md_lines.append("")
            for cc in sorted(codes["cont"], key=lambda x: x["ordinal"]):
                topic = extract_topic_hint(raw_section_5, cc["code"])
                if topic:
                    md_lines.append(f"- `{cc['code']}` {topic}")
                else:
                    md_lines.append(f"- `{cc['code']}`（學習內容第 {cc['ordinal']} 項）")
            md_lines.append("")
        # 學習表現（performance）— 教學目標
        if codes["perf"]:
            md_lines.append("**學習表現**：")
            md_lines.append("")
            for pc in sorted(codes["perf"], key=lambda x: x["ordinal"]):
                md_lines.append(f"- `{pc['code']}`（學生能做到第 {pc['ordinal']} 項表現）")
            md_lines.append("")

    # 教學活動建議（基於 SDT 三大需求）
    md_lines.extend([
        "## 教學活動建議",
        "",
        "依 SDT（自我決定理論）三大需求設計活動：",
        "",
        "- **自主（Autonomy）**：讓學生選擇想探索的主題、決定呈現方式",
        "- **勝任（Competence）**：設計符合個人程度的挑戰、提供即時回饋",
        "- **關聯（Relatedness）**：小組合作、分享創作、同儕觀摩",
        "",
        "**對齊 §15 章**：本領域/階段若要設計成遊戲關卡，請參考 §docs/sdt-design-audit-framework.md 的三道閘門。",
        "",
        "## 學習評量建議",
        "",
        "- 形成性評量：每章節後的小任務 / 學習單",
        "- 總結性評量：單元作品 / 實作表現 / 同儕互評",
        "- 學習歷程：作品集 + 反思日誌",
        "",
    ])

    return "\n".join(md_lines)


def write_textbook_md(domain: str, stage: str, body: str, structured: dict, output_dir: Path):
    """寫一個 .md 到 textbooks/<domain>/。"""
    stage_label, stage_desc = STAGE_NAMES.get(stage, (stage, stage))
    fname = f"stage-{stage}-{slugify(stage_desc)}.md"
    out = output_dir / fname
    all_codes_in_stage = []
    by_stage = get_codes_by_stage_cat(structured)
    for (s, cat), codes in by_stage.items():
        if s == stage:
            all_codes_in_stage.extend([c["code"] for c in codes["perf"] + codes["cont"]])
    fm = {
        "title": f"{domain} — {stage_desc}",
        "domain": domain,
        "stage": stage,
        "stage_desc": stage_desc,
        "source": "AI-generated based on 108 課綱（衍生自 curriculum/<domain>/...）",
        "source_curriculum": f"curriculum/{domain}/",
        "license": "CC BY 4.0（underlying 108 課綱）",
        "generated_date": now_iso(),
        "aligned_codes": sorted(set(all_codes_in_stage)),
    }
    front_matter = "---\n" + "\n".join(
        f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (list, str)) else v}"
        for k, v in fm.items()
    ) + "\n---\n\n"
    out.write_text(front_matter + body + "\n", encoding="utf-8")
    return out


def process_domain(domain: str, output_dir: Path) -> list[Path]:
    """處理單一領域。"""
    domain_dir = CURRICULUM / domain
    sj_files = list(domain_dir.glob("*.structured.json"))
    if not sj_files:
        log(f"  ✗ {domain} 找不到 structured.json")
        return []
    sj = sj_files[0]
    structured = json.loads(sj.read_text(encoding="utf-8"))

    stages = structured.get("stages_present", [])
    if not stages:
        log(f"  ✗ {domain} 沒有 stages_present")
        return []

    log(f"  階段：{stages}")
    tb_dir = output_dir / domain
    tb_dir.mkdir(parents=True, exist_ok=True)

    raw = structured.get("raw_section_5", "")
    outputs = []
    for stage in stages:
        body = generate_textbook(domain, structured, stage, raw)
        out = write_textbook_md(domain, stage, body, structured, tb_dir)
        log(f"    ✓ {stage} → {out.relative_to(ROOT)}")
        outputs.append(out)
    return outputs


def main():
    parser = argparse.ArgumentParser(description="§15-D：自動從 curriculum 生成 AI 教材 .md")
    parser.add_argument("--all", action="store_true", help="5 個缺漏領域全做")
    parser.add_argument("--domain", type=str, help="指定領域")
    parser.add_argument("--out", type=str, default="textbooks/generated",
                        help="輸出目錄（相對 repo 根）")
    args = parser.parse_args()

    log("=== generate_textbooks.py ===")

    if args.all:
        targets = MISSING_DOMAINS
    elif args.domain:
        targets = [args.domain]
    else:
        targets = MISSING_DOMAINS

    output_dir = ROOT / args.out
    output_dir.mkdir(parents=True, exist_ok=True)

    all_outputs = []
    for d in targets:
        log(f"\n[{d}]")
        outputs = process_domain(d, output_dir)
        all_outputs.extend(outputs)

    log(f"\n=== 完成 ===")
    log(f"總共寫了 {len(all_outputs)} 個教材 .md")
    log(f"輸出目錄：{output_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
