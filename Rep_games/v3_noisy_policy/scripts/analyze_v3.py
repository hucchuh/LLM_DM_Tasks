from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"
BEHAVIOR_ORDER = ["stable_moderate", "strategic_opportunist", "noisy_repairing", "apology_only_exploiter"]
LANGUAGE_ORDER = ["neutral", "warm_promise", "apology_excuse"]
COLORS = {
    "neutral": "#235789",
    "warm_promise": "#0f766e",
    "apology_excuse": "#d97706",
}


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
        "observed_return": avg([r["average_return_fraction"] for r in ok]),
        "observed_low": avg([r["low_stake_return_fraction"] for r in ok]),
        "observed_medium": avg([r["medium_stake_return_fraction"] for r in ok]),
        "observed_high": avg([r["high_stake_return_fraction"] for r in ok]),
        "trust_rating": avg(metric("trust_rating")),
        "trust_rating_sd": sd(metric("trust_rating")),
        "predicted_low": avg(metric("predicted_return_fraction_if_low_stake")),
        "predicted_medium": avg(metric("predicted_return_fraction_if_medium_stake")),
        "predicted_high": avg(metric("predicted_return_fraction_if_high_stake")),
        "predicted_high_minus_low": avg(metric("predicted_high_minus_low")),
        "investment_low": avg(metric("investment_if_low_stake")),
        "investment_medium": avg(metric("investment_if_medium_stake")),
        "investment_high": avg(metric("investment_if_high_stake")),
        "message_weight": avg(metric("message_weight")),
        "behavior_weight": avg(metric("behavior_weight")),
        "confidence": avg(metric("confidence")),
    }


def grouped(rows: list[dict], keys: tuple[str, ...]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        key = " / ".join(str(row[k]) for k in keys)
        groups[key].append(row)
    return groups


def ordered_cell_keys(cells: dict[str, dict]) -> list[str]:
    desired = [f"{b} / {l}" for b in BEHAVIOR_ORDER for l in LANGUAGE_ORDER]
    return [key for key in desired if key in cells]


def language_effects(cell_summary: dict[str, dict]) -> dict:
    effects = {}
    for behavior in BEHAVIOR_ORDER:
        base = cell_summary.get(f"{behavior} / neutral")
        if not base:
            continue
        effects[behavior] = {}
        for language in ["warm_promise", "apology_excuse"]:
            item = cell_summary.get(f"{behavior} / {language}")
            if not item:
                continue
            effects[behavior][language] = {
                "delta_trust_vs_neutral": None if item["trust_rating"] is None or base["trust_rating"] is None else round(item["trust_rating"] - base["trust_rating"], 3),
                "delta_predicted_high_vs_neutral": None if item["predicted_high"] is None or base["predicted_high"] is None else round(item["predicted_high"] - base["predicted_high"], 3),
                "delta_investment_high_vs_neutral": None if item["investment_high"] is None or base["investment_high"] is None else round(item["investment_high"] - base["investment_high"], 3),
            }
    return effects


def make_plots(summary: dict) -> None:
    FIG.mkdir(exist_ok=True)
    cells = summary["by_cell"]
    width = 0.24
    x = list(range(len(BEHAVIOR_ORDER)))

    fig, ax = plt.subplots(figsize=(11, 5.4))
    for i, language in enumerate(LANGUAGE_ORDER):
        vals = [cells.get(f"{b} / {language}", {}).get("trust_rating") or 0 for b in BEHAVIOR_ORDER]
        pos = [p + (i - 1) * width for p in x]
        ax.bar(pos, vals, width=width, label=language, color=COLORS[language])
    ax.set_xticks(x, BEHAVIOR_ORDER, rotation=15, ha="right")
    ax.set_ylim(0, 100)
    ax.set_ylabel("trust_rating")
    ax.set_title("V3 Trust Rating: Same Behavior Pattern, Different Language Frame")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "trust_by_behavior_language.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.4))
    for i, language in enumerate(LANGUAGE_ORDER):
        vals = [cells.get(f"{b} / {language}", {}).get("predicted_high_minus_low") or 0 for b in BEHAVIOR_ORDER]
        pos = [p + (i - 1) * width for p in x]
        ax.bar(pos, vals, width=width, label=language, color=COLORS[language])
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_xticks(x, BEHAVIOR_ORDER, rotation=15, ha="right")
    ax.set_ylabel("predicted high return minus low return")
    ax.set_title("V3 High-Low Prediction Gap")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "high_low_gap_by_behavior_language.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    for language in LANGUAGE_ORDER:
        vals = [summary["by_language"].get(language, {}).get("trust_rating") or 0]
        ax.bar(language, vals[0], color=COLORS[language])
    ax.set_ylim(0, 100)
    ax.set_ylabel("trust_rating")
    ax.set_title("V3 Language Main Effect on Trust Rating")
    fig.tight_layout()
    fig.savefig(FIG / "language_main_effect_trust.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    behavior_vals = [summary["overall"].get("behavior_weight") or 0]
    message_vals = [summary["overall"].get("message_weight") or 0]
    ax.bar(["behavior_weight", "message_weight"], [behavior_vals[0], message_vals[0]], color=["#0f766e", "#d97706"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("self-reported weight")
    ax.set_title("V3 Self-Reported Evidence Weight")
    fig.tight_layout()
    fig.savefig(FIG / "self_reported_weight.png", dpi=180)
    plt.close(fig)


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def make_report(summary: dict) -> None:
    cell_rows = []
    for key in ordered_cell_keys(summary["by_cell"]):
        item = summary["by_cell"][key]
        behavior, language = key.split(" / ")
        cell_rows.append(
            f"<tr><td>{behavior}</td><td>{language}</td><td>{item['n_success']}/{item['n_total']}</td>"
            f"<td>{fmt(item['observed_return'])}</td><td>{fmt(item['observed_low'])}</td><td>{fmt(item['observed_high'])}</td>"
            f"<td>{fmt(item['trust_rating'])}</td><td>{fmt(item['predicted_low'])}</td><td>{fmt(item['predicted_high'])}</td>"
            f"<td>{fmt(item['predicted_high_minus_low'])}</td><td>{fmt(item['message_weight'])}</td><td>{fmt(item['behavior_weight'])}</td></tr>"
        )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V3 Noisy Policy Inference</title>
  <style>
    body {{ font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 34px; color: #17202a; line-height: 1.55; }}
    h1 {{ margin-bottom: 6px; }}
    h2 {{ margin: 28px 0 10px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; font-size: 14px; }}
    th,td {{ border: 1px solid #d8dee6; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    img {{ max-width: 100%; border: 1px solid #d8dee6; border-radius: 8px; margin: 10px 0 20px; }}
    .note {{ max-width: 980px; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin:16px 0 22px; }}
    .card {{ border:1px solid #d8dee6; border-radius:8px; padding:12px 14px; background:#f8fafc; }}
    code {{ background:#eef2f7; padding:1px 5px; border-radius:4px; }}
  </style>
</head>
<body>
  <h1>V3 Noisy Policy Inference</h1>
  <p class="note">V3 crosses behavior pattern and language frame. Every observed history has average return 0.40, but individual return fractions are noisy. This tests whether language changes trust or prediction after behavior is controlled.</p>
  <p>Successful calls: {summary['overall']['n_success']} / {summary['overall']['n_total']}.</p>
  <div class="grid">
    <div class="card"><strong>Behavior patterns</strong><br>stable, strategic, repairing, deteriorating</div>
    <div class="card"><strong>Language frames</strong><br>neutral, warm promise, apology/excuse</div>
    <div class="card"><strong>Main test</strong><br>same behavior, different language</div>
  </div>
  <h2>Figures</h2>
  <img src="figures/trust_by_behavior_language.png" alt="Trust by behavior and language">
  <img src="figures/high_low_gap_by_behavior_language.png" alt="High low gap by behavior and language">
  <img src="figures/language_main_effect_trust.png" alt="Language main effect on trust">
  <img src="figures/self_reported_weight.png" alt="Self reported evidence weight">
  <h2>Cell Summary</h2>
  <table>
    <thead><tr><th>Behavior</th><th>Language</th><th>N</th><th>Observed return</th><th>Observed low</th><th>Observed high</th><th>Trust</th><th>Pred low</th><th>Pred high</th><th>High-low gap</th><th>Message weight</th><th>Behavior weight</th></tr></thead>
    <tbody>{''.join(cell_rows)}</tbody>
  </table>
</body>
</html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")


def main() -> None:
    rows = load_results()
    by_behavior_raw = grouped(rows, ("behavior_pattern",))
    by_language_raw = grouped(rows, ("language_frame",))
    by_cell_raw = grouped(rows, ("behavior_pattern", "language_frame"))
    by_cell = {key: aggregate(value) for key, value in sorted(by_cell_raw.items())}
    summary = {
        "overall": aggregate(rows),
        "by_behavior": {key: aggregate(value) for key, value in sorted(by_behavior_raw.items())},
        "by_language": {key: aggregate(value) for key, value in sorted(by_language_raw.items())},
        "by_cell": by_cell,
        "language_effects_vs_neutral": language_effects(by_cell),
        "errors": [r["error"] for r in rows if r.get("error")],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    make_plots(summary)
    make_report(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

