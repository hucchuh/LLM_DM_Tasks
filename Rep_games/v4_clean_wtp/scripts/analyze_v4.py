from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"
BEHAVIOR_ORDER = ["stable_moderate", "strategic_opportunist", "noisy_repairing", "deteriorating_exploiter"]
LANGUAGE_ORDER = ["neutral_filler", "warmth", "promise", "apology"]
STAKE_ORDER = ["low", "medium", "high"]
BEHAVIOR_LABELS = {
    "stable_moderate": "Stable moderate",
    "strategic_opportunist": "Strategic opportunist",
    "noisy_repairing": "Noisy repairing",
    "deteriorating_exploiter": "Deteriorating exploiter",
}
LANGUAGE_LABELS = {
    "neutral_filler": "Neutral",
    "warmth": "Warmth",
    "promise": "Promise",
    "apology": "Apology",
}
COLORS = {
    "neutral_filler": "#334155",
    "warmth": "#0f766e",
    "promise": "#2563eb",
    "apology": "#d97706",
}


def load_results() -> list[dict]:
    path = OUT / "results.json"
    if not path.exists():
        path = OUT / "results_partial.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ok_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r.get("error") and r.get("metrics")]


def avg(values: list[float | int | bool | None]) -> float | None:
    numeric = [float(v) for v in values if v is not None]
    if not numeric:
        return None
    return round(mean(numeric), 3)


def sd(values: list[float | int | None]) -> float | None:
    numeric = [float(v) for v in values if v is not None]
    if len(numeric) < 2:
        return None
    return round(pstdev(numeric), 3)


def aggregate(rows: list[dict]) -> dict:
    ok = ok_rows(rows)
    def metric(key: str) -> list:
        return [r["metrics"].get(key) for r in ok if r["metrics"].get(key) is not None]
    return {
        "n_total": len(rows),
        "n_success": len(ok),
        "observed_return": avg([r.get("average_return_fraction") for r in ok]),
        "observed_low": avg([r.get("low_stake_return_fraction") for r in ok]),
        "observed_medium": avg([r.get("medium_stake_return_fraction") for r in ok]),
        "observed_high": avg([r.get("high_stake_return_fraction") for r in ok]),
        "final_two_return": avg([r.get("final_two_return_fraction") for r in ok]),
        "policy_next_return": avg([r.get("generated_policy_return_for_next_stake") for r in ok]),
        "continue_rate": avg(metric("continue_choice")),
        "willingness_to_pay": avg(metric("willingness_to_pay")),
        "willingness_to_pay_sd": sd(metric("willingness_to_pay")),
        "next_investment": avg(metric("next_investment")),
        "investment_fraction": avg(metric("investment_fraction")),
        "trust_rating": avg(metric("trust_rating")),
        "trust_rating_sd": sd(metric("trust_rating")),
    }


def grouped(rows: list[dict], keys: tuple[str, ...]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[" / ".join(str(row[k]) for k in keys)].append(row)
    return groups


def language_effects_within_yoke(rows: list[dict]) -> dict:
    ok = ok_rows(rows)
    by_history: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in ok:
        by_history[row["history_id"]][row["language_frame"]] = row

    effects: dict[str, dict[str, dict[str, float | int | None]]] = defaultdict(lambda: defaultdict(dict))
    for behavior in BEHAVIOR_ORDER:
        histories = [items for hid, items in by_history.items() if hid.startswith(behavior)]
        for language in [l for l in LANGUAGE_ORDER if l != "neutral_filler"]:
            deltas = {"willingness_to_pay": [], "investment_fraction": [], "trust_rating": []}
            for items in histories:
                neutral = items.get("neutral_filler")
                treatment = items.get(language)
                if not neutral or not treatment:
                    continue
                for key in deltas:
                    nv = neutral["metrics"].get(key)
                    tv = treatment["metrics"].get(key)
                    if nv is not None and tv is not None:
                        deltas[key].append(tv - nv)
            effects[behavior][language] = {
                key: avg(values)
                for key, values in deltas.items()
            } | {"n_yoked": len(deltas["willingness_to_pay"])}
    return {k: dict(v) for k, v in effects.items()}


def make_plots(summary: dict) -> None:
    FIG.mkdir(exist_ok=True)
    cells = summary["by_behavior_language"]
    width = 0.19
    x = list(range(len(BEHAVIOR_ORDER)))

    fig, ax = plt.subplots(figsize=(12, 5.6))
    for i, language in enumerate(LANGUAGE_ORDER):
        vals = [cells.get(f"{b} / {language}", {}).get("willingness_to_pay") or 0 for b in BEHAVIOR_ORDER]
        pos = [p + (i - 1.5) * width for p in x]
        bars = ax.bar(pos, vals, width=width, label=LANGUAGE_LABELS[language], color=COLORS[language])
        for bar, value in zip(bars, vals):
            y = value + 0.06 if value > 0 else 0.08
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                y,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
                rotation=90,
                color="#17202a",
            )
    ax.set_xticks(x, [BEHAVIOR_LABELS[b] for b in BEHAVIOR_ORDER], rotation=12, ha="right")
    ax.set_ylim(0, 10)
    ax.set_ylabel("Willingness to pay (0-10)")
    ax.set_title("V4 Costly Continuation: WTP by Behavior and Language")
    ax.legend(ncols=4, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "wtp_by_behavior_language.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.6))
    for i, language in enumerate(LANGUAGE_ORDER):
        vals = [cells.get(f"{b} / {language}", {}).get("trust_rating") or 0 for b in BEHAVIOR_ORDER]
        pos = [p + (i - 1.5) * width for p in x]
        ax.bar(pos, vals, width=width, label=LANGUAGE_LABELS[language], color=COLORS[language])
    ax.set_xticks(x, [BEHAVIOR_LABELS[b] for b in BEHAVIOR_ORDER], rotation=12, ha="right")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Trust rating (0-100)")
    ax.set_title("V4 Trust Rating by Behavior and Language")
    ax.legend(ncols=4, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "trust_by_behavior_language.png", dpi=180)
    plt.close(fig)

    by_behavior_stake = summary["by_behavior_next_stake"]
    fig, ax = plt.subplots(figsize=(10.8, 5.4))
    stake_colors = {"low": "#059669", "medium": "#64748b", "high": "#dc2626"}
    width2 = 0.24
    for i, stake in enumerate(STAKE_ORDER):
        vals = [by_behavior_stake.get(f"{b} / {stake}", {}).get("investment_fraction") or 0 for b in BEHAVIOR_ORDER]
        pos = [p + (i - 1) * width2 for p in x]
        ax.bar(pos, vals, width=width2, label=stake, color=stake_colors[stake])
    ax.set_xticks(x, [BEHAVIOR_LABELS[b] for b in BEHAVIOR_ORDER], rotation=12, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Investment fraction of available tokens")
    ax.set_title("V4 Next Investment by Behavior and Upcoming Stake")
    ax.legend(title="Next stake", ncols=3)
    fig.tight_layout()
    fig.savefig(FIG / "investment_fraction_by_behavior_stake.png", dpi=180)
    plt.close(fig)

    by_language = summary["by_language"]
    fig, ax = plt.subplots(figsize=(8.8, 5))
    vals = [by_language.get(l, {}).get("willingness_to_pay") or 0 for l in LANGUAGE_ORDER]
    ax.bar([LANGUAGE_LABELS[l] for l in LANGUAGE_ORDER], vals, color=[COLORS[l] for l in LANGUAGE_ORDER])
    ax.set_ylim(0, 10)
    ax.set_ylabel("WTP (0-10)")
    ax.set_title("V4 Language Main Effect on WTP")
    fig.tight_layout()
    fig.savefig(FIG / "language_main_effect_wtp.png", dpi=180)
    plt.close(fig)


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def ordered_keys(group_name: str, data: dict) -> list[str]:
    if group_name == "by_behavior_language":
        desired = [f"{b} / {l}" for b in BEHAVIOR_ORDER for l in LANGUAGE_ORDER]
    elif group_name == "by_behavior_next_stake":
        desired = [f"{b} / {s}" for b in BEHAVIOR_ORDER for s in STAKE_ORDER]
    else:
        desired = list(data)
    return [k for k in desired if k in data]


def make_table_rows(summary: dict, group_name: str) -> str:
    rows = []
    for key in ordered_keys(group_name, summary[group_name]):
        item = summary[group_name][key]
        first, second = key.split(" / ")
        rows.append(
            f"<tr><td>{first}</td><td>{second}</td><td>{item['n_success']}/{item['n_total']}</td>"
            f"<td>{fmt(item['observed_return'])}</td><td>{fmt(item['policy_next_return'])}</td>"
            f"<td>{fmt(item['continue_rate'])}</td><td>{fmt(item['willingness_to_pay'])}</td>"
            f"<td>{fmt(item['investment_fraction'])}</td><td>{fmt(item['trust_rating'])}</td></tr>"
        )
    return "".join(rows)


def make_report(summary: dict) -> None:
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V4 Clean WTP Trust Game</title>
  <style>
    body {{ font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 34px; color: #17202a; line-height: 1.56; }}
    h1 {{ margin-bottom: 6px; }}
    h2 {{ margin: 28px 0 10px; }}
    .note {{ max-width: 980px; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin:16px 0 22px; }}
    .card {{ border:1px solid #d8dee6; border-radius:8px; padding:12px 14px; background:#f8fafc; }}
    .metric {{ font-size: 26px; font-weight: 700; display:block; margin-bottom: 2px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; font-size: 14px; }}
    th,td {{ border: 1px solid #d8dee6; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    img {{ max-width: 100%; border: 1px solid #d8dee6; border-radius: 8px; margin: 10px 0 20px; }}
    code {{ background:#eef2f7; padding:1px 5px; border-radius:4px; }}
  </style>
</head>
<body>
  <h1>V4 Clean WTP Trust Game</h1>
  <p class="note">V4 fixes the main V3 confounds: numeric histories are yoked across language frames, stake order is counterbalanced, language is exogenous, and the main task asks for costly choice rather than explicit return estimates.</p>
  <div class="grid">
    <div class="card"><span class="metric">{summary['overall']['n_success']}/{summary['overall']['n_total']}</span>successful API calls</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['observed_return'])}</span>mean observed return</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['willingness_to_pay'])}</span>mean WTP</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['trust_rating'])}</span>mean trust</div>
  </div>
  <h2>Protocol</h2>
  <p class="note">Each trial shows six previous rounds as trial-by-trial records. The model sees no average return, no low/high mean estimate question, and no message-vs-behavior weight probe. It receives one upcoming stake and chooses whether to continue, maximum access fee, investment, and trust rating.</p>
  <h2>Main Figures</h2>
  <p class="note">In the WTP figure, zero-height bars are labeled as 0.00. For deteriorating exploiter, neutral, promise, and apology all have WTP exactly 0; warmth is visible because its mean WTP is 0.17.</p>
  <img src="figures/wtp_by_behavior_language.png" alt="WTP by behavior and language">
  <img src="figures/trust_by_behavior_language.png" alt="Trust by behavior and language">
  <img src="figures/investment_fraction_by_behavior_stake.png" alt="Investment by behavior and stake">
  <img src="figures/language_main_effect_wtp.png" alt="Language main effect on WTP">
  <h2>Behavior x Language</h2>
  <table>
    <thead><tr><th>Behavior</th><th>Language</th><th>N</th><th>Observed mean</th><th>Policy next return</th><th>Continue rate</th><th>WTP</th><th>Investment fraction</th><th>Trust</th></tr></thead>
    <tbody>{make_table_rows(summary, 'by_behavior_language')}</tbody>
  </table>
  <h2>Behavior x Next Stake</h2>
  <table>
    <thead><tr><th>Behavior</th><th>Next stake</th><th>N</th><th>Observed mean</th><th>Policy next return</th><th>Continue rate</th><th>WTP</th><th>Investment fraction</th><th>Trust</th></tr></thead>
    <tbody>{make_table_rows(summary, 'by_behavior_next_stake')}</tbody>
  </table>
</body>
</html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")


def main() -> None:
    rows = load_results()
    summary = {
        "overall": aggregate(rows),
        "by_behavior": {k: aggregate(v) for k, v in sorted(grouped(rows, ("behavior_pattern",)).items())},
        "by_language": {k: aggregate(v) for k, v in sorted(grouped(rows, ("language_frame",)).items())},
        "by_next_stake": {k: aggregate(v) for k, v in sorted(grouped(rows, ("next_stake",)).items())},
        "by_behavior_language": {k: aggregate(v) for k, v in sorted(grouped(rows, ("behavior_pattern", "language_frame")).items())},
        "by_behavior_next_stake": {k: aggregate(v) for k, v in sorted(grouped(rows, ("behavior_pattern", "next_stake")).items())},
        "by_language_next_stake": {k: aggregate(v) for k, v in sorted(grouped(rows, ("language_frame", "next_stake")).items())},
        "within_yoke_language_effects_vs_neutral": language_effects_within_yoke(rows),
        "errors": [r["error"] for r in rows if r.get("error")],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    make_plots(summary)
    make_report(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
