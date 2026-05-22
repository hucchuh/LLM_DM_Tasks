from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"
DISPLAY_LABELS = {
    "stable_warm": "honest_cooperator",
    "stable_neutral": "cautious_reliable",
    "high_stake_betrayal": "strategic_opportunist",
    "high_stake_generous": "strategic_opportunist_mirror",
    "repairing_trend": "noisy_repairing",
    "declining_trend": "apology_only_exploiter",
}
DISPLAY_ORDER = [
    "honest_cooperator",
    "cautious_reliable",
    "strategic_opportunist",
    "strategic_opportunist_mirror",
    "noisy_repairing",
    "apology_only_exploiter",
]


def display_label(raw_label: str) -> str:
    return DISPLAY_LABELS.get(raw_label, raw_label)


def ordered_keys(items: dict) -> list[str]:
    label_rank = {label: i for i, label in enumerate(DISPLAY_ORDER)}
    return sorted(items.keys(), key=lambda key: label_rank.get(display_label(key), 999))


def load_results() -> list[dict]:
    path = OUT / "results_partial.json"
    if not path.exists():
        path = OUT / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ok_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r.get("error") and r.get("metrics")]


def avg(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return None if not values else round(mean(values), 3)


def sd(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return None if len(values) < 2 else round(pstdev(values), 3)


def aggregate(rows: list[dict]) -> dict:
    ok = ok_rows(rows)
    def metric(key: str) -> list[float]:
        return [r["metrics"].get(key) for r in ok if r["metrics"].get(key) is not None]
    return {
        "n_total": len(rows),
        "n_success": len(ok),
        "average_return_fraction": avg([r["average_return_fraction"] for r in ok]),
        "low_stake_return_fraction": avg([r["low_stake_return_fraction"] for r in ok]),
        "medium_stake_return_fraction": avg([r["medium_stake_return_fraction"] for r in ok]),
        "high_stake_return_fraction": avg([r["high_stake_return_fraction"] for r in ok]),
        "global_trust_rating": avg(metric("global_trust_rating")),
        "global_trust_rating_sd": sd(metric("global_trust_rating")),
        "message_credibility": avg(metric("message_credibility")),
        "policy_structure_rating": avg(metric("policy_structure_rating")),
        "predicted_return_low": avg(metric("predicted_return_fraction_if_low_stake")),
        "predicted_return_medium": avg(metric("predicted_return_fraction_if_medium_stake")),
        "predicted_return_high": avg(metric("predicted_return_fraction_if_high_stake")),
        "predicted_high_minus_low": avg(metric("predicted_high_minus_low")),
        "investment_low": avg(metric("investment_if_low_stake")),
        "investment_medium": avg(metric("investment_if_medium_stake")),
        "investment_high": avg(metric("investment_if_high_stake")),
        "investment_fraction_low": avg(metric("investment_fraction_if_low_stake")),
        "investment_fraction_medium": avg(metric("investment_fraction_if_medium_stake")),
        "investment_fraction_high": avg(metric("investment_fraction_if_high_stake")),
        "confidence": avg(metric("confidence")),
    }


def make_plots(summary: dict) -> None:
    FIG.mkdir(exist_ok=True)
    items = summary["by_condition"]
    raw_labels = ordered_keys(items)
    labels = [display_label(key) for key in raw_labels]
    colors = ["#235789", "#0f766e", "#be123c", "#7c3aed", "#d97706", "#475569"]

    fig, ax = plt.subplots(figsize=(10, 5))
    trust = [items[x]["global_trust_rating"] or 0 for x in raw_labels]
    ax.barh(labels, trust, color=colors[: len(labels)])
    ax.set_xlim(0, 100)
    ax.set_xlabel("trust_rating")
    ax.set_title("Trust Rating by Partner Type, Observed Return Controlled at 0.40")
    fig.tight_layout()
    fig.savefig(FIG / "global_trust_by_condition.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = [0, 1, 2]
    stake_labels = ["low", "medium", "high"]
    for idx, key in enumerate(raw_labels):
        vals = [
            items[key]["predicted_return_low"],
            items[key]["predicted_return_medium"],
            items[key]["predicted_return_high"],
        ]
        ax.plot(x, vals, marker="o", linewidth=2, label=display_label(key), color=colors[idx % len(colors)])
    ax.set_xticks(x, stake_labels)
    ax.set_ylim(0.15, 0.65)
    ax.set_ylabel("predicted return")
    ax.set_title("Predicted Return by Stake")
    ax.legend(fontsize=8, ncols=2)
    ax.grid(True, color="#e5e7eb")
    fig.tight_layout()
    fig.savefig(FIG / "conditional_return_predictions.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    gaps = [items[x]["predicted_high_minus_low"] or 0 for x in raw_labels]
    ax.barh(labels, gaps, color=colors[: len(labels)])
    ax.axvline(0, color="#111827", linewidth=1)
    ax.set_xlabel("predicted high-stake return minus predicted low-stake return")
    ax.set_title("High-Low Prediction Gap by Partner Type")
    fig.tight_layout()
    fig.savefig(FIG / "predicted_high_minus_low_by_condition.png", dpi=180)
    plt.close(fig)


def make_report(summary: dict) -> None:
    rows = []
    for key in ordered_keys(summary["by_condition"]):
        item = summary["by_condition"][key]
        rows.append(
            f"<tr><td>{display_label(key)}</td><td>{item['n_success']}/{item['n_total']}</td>"
            f"<td>{item['global_trust_rating']}</td>"
            f"<td>{item['average_return_fraction']}</td>"
            f"<td>{item['low_stake_return_fraction']}</td>"
            f"<td>{item['high_stake_return_fraction']}</td>"
            f"<td>{item['predicted_return_low']}</td>"
            f"<td>{item['predicted_return_high']}</td>"
            f"<td>{item['predicted_high_minus_low']}</td></tr>"
        )
    trust_min = min(
        item["global_trust_rating"]
        for item in summary["by_condition"].values()
        if item["global_trust_rating"] is not None
    )
    trust_max = max(
        item["global_trust_rating"]
        for item in summary["by_condition"].values()
        if item["global_trust_rating"] is not None
    )
    betrayal = summary["by_condition"]["high_stake_betrayal"]
    generous = summary["by_condition"]["high_stake_generous"]
    declining = summary["by_condition"]["declining_trend"]
    repairing = summary["by_condition"]["repairing_trend"]
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V2 Repeated Trust Game: V1 Partner Types With Average Return Control</title>
  <style>
    body {{ font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 34px; color: #17202a; line-height: 1.55; }}
    h1 {{ margin-bottom: 6px; }}
    h2 {{ margin: 30px 0 10px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
    th,td {{ border: 1px solid #d8dee6; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    img {{ max-width: 100%; border: 1px solid #d8dee6; border-radius: 8px; margin: 10px 0 20px; }}
    .note {{ max-width: 980px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 16px 0 22px; }}
    .card {{ border: 1px solid #d8dee6; border-radius: 8px; padding: 12px 14px; background: #f8fafc; }}
    .card strong {{ display: block; margin-bottom: 4px; }}
    code {{ background: #eef2f7; padding: 1px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>V2 Repeated Trust Game: V1 Partner Types With Average Return Control</h1>
  <p class="note">This is the controlled follow-up to v1. V1 showed that <code>trust_rating</code> closely tracks <code>observed return</code>. V2 keeps the same partner-type language as v1, but implements average-return-controlled variants. Every partner type has exactly the same observed average return, <code>0.40</code>, while the pattern of returns differs across stake and time.</p>
  <p>Successful calls: {summary['overall']['n_success']} / {summary['overall']['n_total']}.</p>

  <h2>Question</h2>
  <p class="note">If the model only uses average return, all partner types should receive similar <code>trust_rating</code> and similar <code>predicted return</code>. If the model represents a more structured partner pattern, then the conditional predictions should change with the partner's actual low-stake and high-stake behavior.</p>

  <div class="cards">
    <div class="card"><strong>Controlled variable</strong>Observed average return = 0.40 for every partner type.</div>
    <div class="card"><strong>Main dependent variables</strong><code>trust_rating</code>, <code>predicted return</code>, and conditional investment.</div>
    <div class="card"><strong>New v2 readout</strong><code>High-low prediction gap</code> = predicted high-stake return minus predicted low-stake return.</div>
  </div>

  <h2>Main Pattern</h2>
  <p class="note">The model does not behave as if average return is the whole story. Although every partner type has the same observed average return, <code>trust_rating</code> ranges from {trust_min} to {trust_max}. More importantly, the conditional <code>predicted return</code> tracks the actual stake-dependent pattern.</p>
  <ul>
    <li><code>strategic_opportunist</code>: observed low/high return = {betrayal['low_stake_return_fraction']} / {betrayal['high_stake_return_fraction']}; predicted low/high return = {betrayal['predicted_return_low']} / {betrayal['predicted_return_high']}.</li>
    <li><code>strategic_opportunist_mirror</code>: observed low/high return = {generous['low_stake_return_fraction']} / {generous['high_stake_return_fraction']}; predicted low/high return = {generous['predicted_return_low']} / {generous['predicted_return_high']}.</li>
    <li><code>apology_only_exploiter</code>: same average return, but low trust ({declining['global_trust_rating']}) because recent behavior deteriorates.</li>
    <li><code>noisy_repairing</code>: same average return, but higher predicted future returns because later rounds show repair and compensation.</li>
  </ul>

  <h2>Figures</h2>
  <img src="figures/global_trust_by_condition.png" alt="Global trust by condition">
  <img src="figures/conditional_return_predictions.png" alt="Conditional return predictions">
  <img src="figures/predicted_high_minus_low_by_condition.png" alt="High minus low prediction gap">

  <h2>Partner Type Summary</h2>
  <table>
    <thead><tr><th>Partner type</th><th>N</th><th>Trust rating</th><th>Observed return</th><th>Observed low-stake return</th><th>Observed high-stake return</th><th>Predicted low-stake return</th><th>Predicted high-stake return</th><th>High-low prediction gap</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>Interpretation</h2>
  <p class="note">V2 revises the simple v1 reading. The model clearly uses revealed returns, but it is not limited to a single average-return score. Under average-return control, it can recover stake-dependent return patterns. The cleaner conclusion is: <code>trust_rating</code> is a coarse summary, while conditional <code>predicted return</code> is the better probe of whether the model represents the partner's behavior pattern.</p>
</body>
</html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")


def main() -> None:
    rows = load_results()
    groups = defaultdict(list)
    for row in rows:
        groups[row["condition"]].append(row)
    by_condition = {key: aggregate(value) for key, value in sorted(groups.items())}
    summary = {
        "overall": aggregate(rows),
        "by_condition": by_condition,
        "errors": [r["error"] for r in rows if r.get("error")],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    make_plots(summary)
    make_report(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
