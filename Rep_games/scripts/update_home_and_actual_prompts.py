from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "v1_v4_integrated_experiment_report.html"


EXAMPLES = [
    {
        "version": "V1",
        "title": "会说话但少返还者：真实输入和输出",
        "path": ROOT / "output" / "results.json",
        "filter": {"partner_type": "charming_under_returner"},
        "meta": ["trial_id", "partner_type", "repetition", "true_mean_return_fraction", "high_stake_return_fraction"],
    },
    {
        "version": "V2",
        "title": "高赌注背叛：平均返还相同但结构不同",
        "path": ROOT / "v2_average_control" / "output" / "results.json",
        "filter": {"condition": "high_stake_betrayal"},
        "meta": ["trial_id", "condition", "repetition", "average_return_fraction", "low_stake_return_fraction", "high_stake_return_fraction"],
    },
    {
        "version": "V3",
        "title": "机会主义 + 道歉解释：噪声记录中的语言条件",
        "path": ROOT / "v3_noisy_policy" / "output" / "results.json",
        "filter": {"behavior_pattern": "strategic_opportunist", "language_frame": "apology_excuse"},
        "meta": ["trial_id", "behavior_pattern", "language_frame", "repetition", "average_return_fraction", "high_stake_return_fraction"],
    },
    {
        "version": "V4",
        "title": "机会主义 + 道歉 + 高赌注：同一行为记录只换说法",
        "path": ROOT / "v4_clean_wtp" / "output" / "results.json",
        "filter": {"behavior_pattern": "strategic_opportunist", "language_frame": "apology", "next_stake": "high"},
        "meta": ["trial_id", "behavior_pattern", "language_frame", "next_stake", "average_return_fraction", "high_stake_return_fraction"],
    },
]


def pick_example(spec: dict) -> dict:
    rows = json.loads(spec["path"].read_text(encoding="utf-8"))
    for row in rows:
        if row.get("error"):
            continue
        if all(row.get(key) == value for key, value in spec["filter"].items()):
            return row
    raise RuntimeError(f"No matching example for {spec['version']}: {spec['filter']}")


def format_meta(row: dict, keys: list[str]) -> str:
    parts = []
    for key in keys:
        if key in row:
            parts.append(f"{key}: {row[key]}")
    return " · ".join(parts)


def make_prompt_box(spec: dict) -> str:
    row = pick_example(spec)
    prompt = html.escape(row.get("prompt", ""), quote=False)
    output = html.escape(row.get("raw_content", ""), quote=False)
    meta = html.escape(format_meta(row, spec["meta"]), quote=False)
    parsed = row.get("parsed")
    parsed_json = html.escape(json.dumps(parsed, ensure_ascii=False, indent=2), quote=False) if parsed is not None else ""

    parsed_block = ""
    if parsed_json:
        parsed_block = f"""
          <details>
            <summary>解析后的字段</summary>
            <pre>{parsed_json}</pre>
          </details>"""

    return f"""
        <div class="prompt-box prompt-io">
          <h3>{html.escape(spec["version"])}：{html.escape(spec["title"])}</h3>
          <p class="prompt-meta">{meta}</p>
          <details open>
            <summary>真实输入 prompt</summary>
            <pre>{prompt}</pre>
          </details>
          <details open>
            <summary>模型原始输出</summary>
            <pre>{output}</pre>
          </details>{parsed_block}
        </div>"""


def build_appendix() -> str:
    boxes = "\n".join(make_prompt_box(spec) for spec in EXAMPLES)
    return f"""    <section>
      <div class="wrap">
        <h2>附录：真实输入和输出示例</h2>
        <p class="lead">这里使用实验运行时实际发送给模型的 prompt 和模型返回的原始 JSON。每版只放一个代表性试次；完整记录在各版本的 <code>output/results.json</code> 中。</p>
{boxes}
      </div>
    </section>"""


def update_html() -> None:
    text = HTML.read_text(encoding="utf-8")

    text = re.sub(
        r"""      background:\n        linear-gradient\(90deg, rgba\(15, 23, 42, 0\.88\), rgba\(15, 23, 42, 0\.50\)\),\n        url\("figures_cn/v4_wtp_by_behavior_language_cn\.png"\);""",
        """      background:
        linear-gradient(120deg, rgba(17, 24, 39, 0.98), rgba(35, 87, 137, 0.90)),
        repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.06) 0 1px, transparent 1px 88px),
        repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.045) 0 1px, transparent 1px 88px);""",
        text,
    )

    text = re.sub(
        r"""\n      <div class="hero-meta">\n        <span class="tag">.*?</span>\n        <span class="tag">.*?</span>\n        <span class="tag">.*?</span>\n        <span class="tag">.*?</span>\n      </div>""",
        "",
        text,
        flags=re.S,
    )

    text = re.sub(
        r"""\n    \.hero-meta \{\n      display: flex;\n      flex-wrap: wrap;\n      gap: 12px;\n      margin-top: 34px;\n    \}\n\n    \.tag \{\n      border: 1px solid rgba\(255, 255, 255, 0\.38\);\n      background: rgba\(255, 255, 255, 0\.10\);\n      color: white;\n      padding: 7px 12px;\n      border-radius: 999px;\n      font-size: 14px;\n    \}\n""",
        "\n",
        text,
        flags=re.S,
    )

    if ".prompt-io details" not in text:
        text = text.replace(
            """    .prompt-box {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 18px;
      margin-top: 18px;
    }
""",
            """    .prompt-box {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 18px;
      margin-top: 18px;
    }

    .prompt-meta {
      color: var(--muted);
      font-size: 14px;
    }

    .prompt-io details {
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
      overflow: hidden;
    }

    .prompt-io summary {
      cursor: pointer;
      padding: 10px 14px;
      font-weight: 650;
      color: var(--ink);
    }
""",
        )

    text = text.replace(
        """      overflow: auto;
      margin: 12px 0 0;""",
        """      overflow: auto;
      max-height: 520px;
      margin: 12px 0 0;""",
    )

    start = text.index('    <section>\n      <div class="wrap">\n        <h2>附录：')
    end = text.index("\n  </main>", start)
    text = text[:start] + build_appendix() + text[end:]

    HTML.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {HTML}")


if __name__ == "__main__":
    update_html()
