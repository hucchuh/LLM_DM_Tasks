from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def load_results() -> list[dict]:
    path = OUT / "results_partial.json"
    if not path.exists():
        path = OUT / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r.get("error") and r.get("metrics")]
    def avg(key: str):
        vals = [r["metrics"].get(key) for r in ok if r["metrics"].get(key) is not None]
        return None if not vals else round(mean(vals), 3)
    return {
        "n_total": len(rows),
        "n_success": len(ok),
        "mean_investment_next": avg("investment_next"),
        "mean_predicted_return_fraction_next": avg("predicted_return_fraction_next"),
        "mean_trust_rating": avg("trust_rating"),
        "mean_confidence": avg("confidence"),
        "mean_true_return_fraction": None if not ok else round(mean(r["true_mean_return_fraction"] for r in ok), 3),
        "mean_high_stake_return_fraction": None if not [r for r in ok if r["high_stake_return_fraction"] is not None] else round(mean(r["high_stake_return_fraction"] for r in ok if r["high_stake_return_fraction"] is not None), 3),
    }


def successful_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r.get("error") and r.get("metrics")]


def linear_fit(points: list[tuple[float, float]]) -> dict:
    if len(points) < 2:
        return {"n": len(points), "r": None, "slope": None, "intercept": None}
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    x_bar = mean(xs)
    y_bar = mean(ys)
    ss_x = sum((x - x_bar) ** 2 for x in xs)
    ss_y = sum((y - y_bar) ** 2 for y in ys)
    cov = sum((x - x_bar) * (y - y_bar) for x, y in points)
    if ss_x == 0 or ss_y == 0:
        return {"n": len(points), "r": None, "slope": None, "intercept": None}
    slope = cov / ss_x
    intercept = y_bar - slope * x_bar
    r = cov / ((ss_x * ss_y) ** 0.5)
    return {"n": len(points), "r": round(r, 3), "slope": round(slope, 3), "intercept": round(intercept, 3)}


def relationship_summary(rows: list[dict], by_partner_type: dict) -> dict:
    ok = successful_rows(rows)
    trial_points = [
        (float(r["true_mean_return_fraction"]), float(r["metrics"]["trust_rating"]))
        for r in ok
        if r.get("true_mean_return_fraction") is not None and r["metrics"].get("trust_rating") is not None
    ]
    type_points = [
        (float(item["mean_true_return_fraction"]), float(item["mean_trust_rating"]))
        for item in by_partner_type.values()
        if item["mean_true_return_fraction"] is not None and item["mean_trust_rating"] is not None
    ]
    return {
        "trial_level_trust_vs_average_return": linear_fit(trial_points),
        "partner_type_mean_trust_vs_average_return": linear_fit(type_points),
    }


def make_report(summary: dict) -> None:
    rows = []
    for key, item in summary["by_partner_type"].items():
        rows.append(
            f"<tr><td>{key}</td><td>{item['n_success']}/{item['n_total']}</td>"
            f"<td>{item['mean_investment_next']}</td>"
            f"<td>{item['mean_trust_rating']}</td>"
            f"<td>{item['mean_predicted_return_fraction_next']}</td>"
            f"<td>{item['mean_true_return_fraction']}</td>"
            f"<td>{item['mean_high_stake_return_fraction']}</td></tr>"
        )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Repeated Trust Game Pilot</title>
  <style>
    body {{ font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 34px; color: #17202a; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th,td {{ border: 1px solid #d8dee6; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; }}
    img {{ max-width: 100%; border: 1px solid #d8dee6; border-radius: 8px; margin: 10px 0 20px; }}
  </style>
</head>
<body>
  <h1>Repeated Trust Game Pilot</h1>
  <p>Successful calls: {summary['overall']['n_success']} / {summary['overall']['n_total']}.</p>
  <img src="figures/investment_by_partner_type.png" alt="Investment by partner type">
  <img src="figures/trust_by_partner_type.png" alt="Trust by partner type">
  <img src="figures/trust_vs_average_return_trials.png" alt="Trust rating vs average return, trial level">
  <img src="figures/trust_vs_average_return_by_type.png" alt="Trust rating vs average return, partner type means">
  <p>Trial-level trust/average-return correlation: r={summary['relationships']['trial_level_trust_vs_average_return']['r']}, n={summary['relationships']['trial_level_trust_vs_average_return']['n']}.</p>
  <p>Partner-type mean trust/average-return correlation: r={summary['relationships']['partner_type_mean_trust_vs_average_return']['r']}, n={summary['relationships']['partner_type_mean_trust_vs_average_return']['n']}.</p>
  <table>
    <thead><tr><th>Partner type</th><th>N</th><th>Investment next</th><th>Trust rating</th><th>Predicted return</th><th>Observed return</th><th>High-stake return</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")


def make_plots(summary: dict) -> None:
    fig_dir = OUT / "figures"
    fig_dir.mkdir(exist_ok=True)
    labels = list(summary["by_partner_type"].keys())
    investment = [summary["by_partner_type"][x]["mean_investment_next"] or 0 for x in labels]
    trust = [summary["by_partner_type"][x]["mean_trust_rating"] or 0 for x in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(labels, investment, color="#0f766e")
    ax.set_xlim(0, 10)
    ax.set_xlabel("investment_next")
    ax.set_title("Next Investment by Partner Type")
    fig.tight_layout()
    fig.savefig(fig_dir / "investment_by_partner_type.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(labels, trust, color="#235789")
    ax.set_xlim(0, 100)
    ax.set_xlabel("trust_rating")
    ax.set_title("Trust Rating by Partner Type")
    fig.tight_layout()
    fig.savefig(fig_dir / "trust_by_partner_type.png", dpi=180)
    plt.close(fig)


def plot_scatter_with_fit(
    points: list[tuple[float, float, str]],
    path: Path,
    title: str,
    fit: dict,
    annotate: bool,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    color_map = {
        "honest_cooperator": "#235789",
        "cautious_reliable": "#0f766e",
        "noisy_repairing": "#7c3aed",
        "strategic_opportunist": "#d97706",
        "charming_under_returner": "#be123c",
        "apology_only_exploiter": "#475569",
    }
    for x, y, label in points:
        ax.scatter(x, y, s=64, color=color_map.get(label, "#111827"), alpha=0.82, edgecolor="white", linewidth=0.8)
        if annotate:
            ax.annotate(label, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8)

    if fit["slope"] is not None and fit["intercept"] is not None:
        xs = [x for x, _, _ in points]
        line_x = [min(xs), max(xs)]
        line_y = [fit["slope"] * x + fit["intercept"] for x in line_x]
        ax.plot(line_x, line_y, color="#111827", linewidth=1.5, alpha=0.75)

    r_label = "NA" if fit["r"] is None else fit["r"]
    ax.text(
        0.03,
        0.95,
        f"r = {r_label}, n = {fit['n']}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": "#d8dee6", "boxstyle": "round,pad=0.3"},
    )
    ax.set_xlim(0.18, 0.56)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Observed average return fraction")
    ax.set_ylabel("Trust rating")
    ax.set_title(title)
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_relationship_plots(rows: list[dict], summary: dict) -> None:
    fig_dir = OUT / "figures"
    ok = successful_rows(rows)
    trial_points = [
        (float(r["true_mean_return_fraction"]), float(r["metrics"]["trust_rating"]), r["partner_type"])
        for r in ok
        if r.get("true_mean_return_fraction") is not None and r["metrics"].get("trust_rating") is not None
    ]
    type_points = [
        (float(item["mean_true_return_fraction"]), float(item["mean_trust_rating"]), key)
        for key, item in summary["by_partner_type"].items()
        if item["mean_true_return_fraction"] is not None and item["mean_trust_rating"] is not None
    ]
    plot_scatter_with_fit(
        trial_points,
        fig_dir / "trust_vs_average_return_trials.png",
        "Trust Rating vs Observed Average Return (Trials)",
        summary["relationships"]["trial_level_trust_vs_average_return"],
        annotate=False,
    )
    plot_scatter_with_fit(
        type_points,
        fig_dir / "trust_vs_average_return_by_type.png",
        "Trust Rating vs Observed Average Return (Partner Type Means)",
        summary["relationships"]["partner_type_mean_trust_vs_average_return"],
        annotate=True,
    )


def main() -> None:
    rows = load_results()
    groups = defaultdict(list)
    for row in rows:
        groups[row["partner_type"]].append(row)
    by_partner_type = {key: aggregate(value) for key, value in sorted(groups.items())}
    summary = {
        "overall": aggregate(rows),
        "by_partner_type": by_partner_type,
        "relationships": relationship_summary(rows, by_partner_type),
        "errors": [r["error"] for r in rows if r.get("error")],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    make_plots(summary)
    make_relationship_plots(rows, summary)
    make_report(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
