from __future__ import annotations

import collections
import html
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
RESULTS = OUT / "results.json"

PARTNER_ORDER = [
    "honest_beneficial",
    "honest_costly",
    "dishonest_beneficial",
    "dishonest_costly",
]

PARTNER_LABELS = {
    "honest_beneficial": "诚实且有帮助",
    "honest_costly": "诚实但有代价",
    "dishonest_beneficial": "不诚实但有帮助",
    "dishonest_costly": "不诚实且有代价",
}

CATEGORIES = [
    (
        "honesty",
        "诚实/说谎",
        r"truth|honest|accur|lied|lie|false|decept|factual|misstatement",
    ),
    (
        "payoff",
        "收益/建议是否赢",
        r"help|win|won|beneficial|payoff|profitable|recommendations? (won|win)|success|advantage|correct recommendations?",
    ),
    (
        "risk",
        "风险/谨慎",
        r"risk|caution|uncertain|moderate|partial|low|avoid|loss|lost|safe",
    ),
    (
        "investment",
        "投资/返还预期",
        r"invest|return|recipro|tokens|expect|money",
    ),
    (
        "pattern",
        "模式/统计",
        r"pattern|strateg|statistic|rate|\d+/?\d+|%|consistent|times",
    ),
    (
        "trust",
        "信任/依赖",
        r"trust|rely|reliable|confidence|trustworthy|untrustworthy",
    ),
]


def load_results() -> list[dict[str, Any]]:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def code_categories(text: str) -> list[str]:
    lowered = (text or "").lower()
    found = []
    for key, _label, pattern in CATEGORIES:
        if re.search(pattern, lowered):
            found.append(key)
    return found or ["other"]


def code_motif(text: str) -> str:
    cats = set(code_categories(text))
    if "honesty" in cats and "payoff" in cats:
        return "诚实与收益同时出现"
    if "payoff" in cats and "honesty" not in cats:
        return "主要谈收益"
    if "honesty" in cats and "payoff" not in cats:
        return "主要谈诚实"
    if "risk" in cats:
        return "主要谈风险"
    return "其他"


def collect_reasons(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    final_reasons = []
    trial_reasons = []
    for row in rows:
        if row.get("error"):
            continue

        metrics = row.get("metrics") or {}
        final_reason = metrics.get("brief_reason", "")
        if final_reason:
            final_reasons.append(
                {
                    "run_id": row["run_id"],
                    "partner_type": row["partner_type"],
                    "presentation_mode": row["presentation_mode"],
                    "reason": final_reason,
                    "categories": code_categories(final_reason),
                    "motif": code_motif(final_reason),
                    "trust_rating": metrics.get("trust_rating"),
                    "willingness_to_pay": metrics.get("willingness_to_pay"),
                    "investment": metrics.get("investment"),
                    "perceived_honesty": metrics.get("perceived_honesty"),
                    "perceived_helpfulness": metrics.get("perceived_helpfulness"),
                }
            )

        for trial in row.get("trial_results") or []:
            trial_reason = (trial.get("trial_parsed") or {}).get("brief_reason", "")
            if trial_reason:
                trial_reasons.append(
                    {
                        "partner_type": row["partner_type"],
                        "presentation_mode": row["presentation_mode"],
                        "round": trial["round"],
                        "reason": trial_reason,
                        "categories": code_categories(trial_reason),
                        "motif": code_motif(trial_reason),
                        "choice": trial.get("model_choice"),
                        "followed_recommendation": trial.get("model_choice") == trial.get("recommended_side"),
                    }
                )
    return final_reasons, trial_reasons


def count_categories(items: list[dict[str, Any]]) -> dict[str, int]:
    counter = collections.Counter(key for item in items for key in item["categories"])
    counts = {key: counter.get(key, 0) for key, _label, _pattern in CATEGORIES}
    counts["other"] = counter.get("other", 0)
    return counts


def pct(value: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{value / total * 100:.0f}%"


def make_summary(final_reasons: list[dict[str, Any]], trial_reasons: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "n_final": len(final_reasons),
        "n_trial_reasons": len(trial_reasons),
        "final_categories": count_categories(final_reasons),
        "trial_categories": count_categories(trial_reasons),
        "by_partner": {},
        "by_mode": {},
        "examples": {},
    }

    for partner in PARTNER_ORDER:
        subset = [item for item in final_reasons if item["partner_type"] == partner]
        summary["by_partner"][partner] = {
            "n": len(subset),
            "categories": count_categories(subset),
            "motifs": dict(collections.Counter(item["motif"] for item in subset)),
        }
        summary["examples"][partner] = [item["reason"] for item in subset[:6]]

    for mode in ["sequential", "batch"]:
        subset = [item for item in final_reasons if item["presentation_mode"] == mode]
        summary["by_mode"][mode] = {
            "n": len(subset),
            "categories": count_categories(subset),
            "motifs": dict(collections.Counter(item["motif"] for item in subset)),
        }

    return summary


def category_rows(items: list[dict[str, Any]]) -> str:
    total = len(items)
    counts = count_categories(items)
    rows = []
    for key, label, _pattern in CATEGORIES:
        rows.append(f"<tr><td>{label}</td><td>{counts[key]}</td><td>{pct(counts[key], total)}</td></tr>")
    rows.append(f"<tr><td>其他</td><td>{counts['other']}</td><td>{pct(counts['other'], total)}</td></tr>")
    return "\n".join(rows)


def partner_rows(final_reasons: list[dict[str, Any]]) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        subset = [item for item in final_reasons if item["partner_type"] == partner]
        counts = count_categories(subset)
        cells = "".join(f"<td>{pct(counts[key], len(subset))}</td>" for key, _label, _pattern in CATEGORIES)
        rows.append(f"<tr><td>{PARTNER_LABELS[partner]}</td><td>{len(subset)}</td>{cells}</tr>")
    return "\n".join(rows)


def example_sections(final_reasons: list[dict[str, Any]]) -> str:
    sections = []
    for partner in PARTNER_ORDER:
        subset = [item for item in final_reasons if item["partner_type"] == partner]
        examples = "\n".join(f"<li>{html.escape(item['reason'])}</li>" for item in subset[:5])
        sections.append(
            f"""
            <section>
              <h2>{PARTNER_LABELS[partner]}：典型输出理由</h2>
              <ul>{examples}</ul>
            </section>
            """
        )
    return "\n".join(sections)


def write_report(final_reasons: list[dict[str, Any]], trial_reasons: list[dict[str, Any]]) -> None:
    final_counts = count_categories(final_reasons)
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V6 motivation coding</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 0; color: #142033; background: #f6f8fb; }}
    header {{ background: #183b5b; color: white; padding: 46px 56px; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 34px; }}
    section {{ background: white; margin: 22px 0; padding: 26px; border: 1px solid #dbe3ec; border-radius: 10px; }}
    h1 {{ font-size: 38px; margin: 0 0 12px; }}
    h2 {{ font-size: 26px; margin: 0 0 16px; }}
    p, li {{ font-size: 18px; line-height: 1.75; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 17px; }}
    th, td {{ padding: 12px; border-bottom: 1px solid #e3e9f0; text-align: left; }}
    th {{ background: #eef4fa; }}
    .note {{ font-size: 18px; color: #42556a; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    .card {{ background: #f8fafc; border: 1px solid #e1e8ef; border-radius: 8px; padding: 18px; }}
    .metric {{ font-size: 34px; font-weight: 800; color: #174a73; }}
    code {{ background: #edf2f7; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>V6 模型输出理由统计</h1>
    <p>基于最终投资决策 JSON 中的 <code>brief_reason</code>；逐轮选牌理由作为辅助分析。</p>
  </header>
  <main>
    <section>
      <h2>读法</h2>
      <p>这里统计的不是模型真正“心里怎么想”，而是它在输出解释中主动调用了哪些理由。一个理由可以同时被编码到多个类别。例如“他经常说谎，但推荐 10/12 次赢了，所以我愿意小额投资”会同时算作诚实、收益、风险和投资返还。</p>
    </section>

    <section>
      <h2>总体结果</h2>
      <div class="grid">
        <div class="card"><div class="metric">{len(final_reasons)}</div><p>最终决策理由</p></div>
        <div class="card"><div class="metric">{len(trial_reasons)}</div><p>逐轮选牌理由</p></div>
        <div class="card"><div class="metric">{final_counts["honesty"]}/{len(final_reasons)}</div><p>最终理由提到诚实或说谎</p></div>
      </div>
    </section>

    <section>
      <h2>最终投资决策：理由类别</h2>
      <table>
        <thead><tr><th>理由类别</th><th>次数</th><th>比例</th></tr></thead>
        <tbody>{category_rows(final_reasons)}</tbody>
      </table>
      <p class="note">最终理由几乎都会提 honesty，但这不意味着最终决策只由 honesty 决定。很多理由的结构是：先识别诚实或不诚实，再根据建议是否带来收益、风险和预期返还决定 WTP 与 investment。</p>
    </section>

    <section>
      <h2>按 partner 类型拆开</h2>
      <table>
        <thead>
          <tr><th>Partner</th><th>N</th>{''.join('<th>' + label + '</th>' for _key, label, _pattern in CATEGORIES)}</tr>
        </thead>
        <tbody>{partner_rows(final_reasons)}</tbody>
      </table>
    </section>

    <section>
      <h2>逐轮选牌理由</h2>
      <table>
        <thead><tr><th>理由类别</th><th>次数</th><th>比例</th></tr></thead>
        <tbody>{category_rows(trial_reasons)}</tbody>
      </table>
      <p class="note">逐轮阶段更常出现“建议是否赢”“模式/统计”“风险/谨慎”。这说明模型在 trial-by-trial 中大量使用局部反馈和胜率，而不是只按 partner 的语言表态行动。</p>
    </section>

    {example_sections(final_reasons)}
  </main>
</body>
</html>
"""
    (OUT / "motivation_report.html").write_text(html_text, encoding="utf-8")


def main() -> None:
    rows = load_results()
    final_reasons, trial_reasons = collect_reasons(rows)
    summary = make_summary(final_reasons, trial_reasons)
    (OUT / "motivation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(final_reasons, trial_reasons)
    print(f"final reasons: {len(final_reasons)}")
    print(f"trial reasons: {len(trial_reasons)}")
    print(f"wrote: {OUT / 'motivation_summary.json'}")
    print(f"wrote: {OUT / 'motivation_report.html'}")


if __name__ == "__main__":
    main()
