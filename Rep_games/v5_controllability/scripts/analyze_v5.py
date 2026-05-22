from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"
PARTNER_ORDER = ["stable_cooperator", "predictable_opportunist", "random_opportunist"]
CONTROL_ORDER = ["controllable_stake", "fixed_high_stake", "random_stake"]
PARTNER_LABELS = {
    "stable_cooperator": "Stable cooperator",
    "predictable_opportunist": "Predictable opportunist",
    "random_opportunist": "Random opportunist",
}
CONTROL_LABELS = {
    "controllable_stake": "Controllable",
    "fixed_high_stake": "Fixed high",
    "random_stake": "Random stake",
}
COLORS = {"controllable_stake": "#0f766e", "fixed_high_stake": "#b42318", "random_stake": "#64748b"}


def load_results() -> list[dict]:
    path = OUT / "results.json"
    if not path.exists():
        path = OUT / "results_partial.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ok_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r.get("error") and r.get("metrics")]


def avg(values: list) -> float | None:
    numeric = [float(v) for v in values if v is not None]
    if not numeric:
        return None
    return round(mean(numeric), 3)


def sd(values: list) -> float | None:
    numeric = [float(v) for v in values if v is not None]
    if len(numeric) < 2:
        return None
    return round(pstdev(numeric), 3)


def grouped(rows: list[dict], keys: tuple[str, ...]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[" / ".join(str(row[k]) for k in keys)].append(row)
    return groups


def aggregate(rows: list[dict]) -> dict:
    ok = ok_rows(rows)

    def metric(key: str) -> list:
        return [r["metrics"].get(key) for r in ok if r["metrics"].get(key) is not None]

    stake_counts = Counter(r["metrics"].get("chosen_stake") for r in ok if r["metrics"].get("chosen_stake"))
    return {
        "n_total": len(rows),
        "n_success": len(ok),
        "observed_return": avg([r.get("average_return_fraction") for r in ok]),
        "observed_low": avg([r.get("low_stake_return_fraction") for r in ok]),
        "observed_medium": avg([r.get("medium_stake_return_fraction") for r in ok]),
        "observed_high": avg([r.get("high_stake_return_fraction") for r in ok]),
        "observed_low_minus_high": avg([r.get("low_minus_high_return_fraction") for r in ok]),
        "return_sd": avg([r.get("return_sd") for r in ok]),
        "continue_rate": avg(metric("continue_choice")),
        "willingness_to_pay": avg(metric("willingness_to_pay")),
        "willingness_to_pay_sd": sd(metric("willingness_to_pay")),
        "trust_rating": avg(metric("trust_rating")),
        "trust_rating_sd": sd(metric("trust_rating")),
        "investment_fraction": avg(metric("investment_fraction")),
        "predicted_low": avg(metric("predicted_return_fraction_if_low_stake")),
        "predicted_medium": avg(metric("predicted_return_fraction_if_medium_stake")),
        "predicted_high": avg(metric("predicted_return_fraction_if_high_stake")),
        "predicted_low_minus_high": avg(metric("predicted_low_minus_high")),
        "chosen_stake_counts": dict(stake_counts),
    }


def controllability_premium(summary: dict) -> dict:
    out = {}
    cells = summary["by_partner_control"]
    for partner in PARTNER_ORDER:
        c = cells.get(f"{partner} / controllable_stake", {}).get("willingness_to_pay")
        h = cells.get(f"{partner} / fixed_high_stake", {}).get("willingness_to_pay")
        r = cells.get(f"{partner} / random_stake", {}).get("willingness_to_pay")
        out[partner] = {
            "controllable_minus_fixed_high": None if c is None or h is None else round(c - h, 3),
            "controllable_minus_random": None if c is None or r is None else round(c - r, 3),
        }
    return out


def make_plots(summary: dict) -> None:
    FIG.mkdir(exist_ok=True)
    cells = summary["by_partner_control"]
    x = list(range(len(PARTNER_ORDER)))
    width = 0.25

    def grouped_bar(metric: str, ylabel: str, title: str, filename: str, ylim: tuple[float, float] | None = None):
        fig, ax = plt.subplots(figsize=(11.5, 5.8))
        for i, control in enumerate(CONTROL_ORDER):
            vals = [cells.get(f"{p} / {control}", {}).get(metric) or 0 for p in PARTNER_ORDER]
            pos = [p + (i - 1) * width for p in x]
            bars = ax.bar(pos, vals, width=width, label=CONTROL_LABELS[control], color=COLORS[control])
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 0.04, f"{val:.2f}", ha="center", va="bottom", fontsize=9)
        ax.set_xticks(x, [PARTNER_LABELS[p] for p in PARTNER_ORDER], rotation=8, ha="right")
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(ncols=3)
        ax.grid(axis="y", alpha=0.18)
        fig.tight_layout()
        fig.savefig(FIG / filename, dpi=180)
        plt.close(fig)

    grouped_bar("willingness_to_pay", "WTP (0-10)", "V5 WTP by partner type and control condition", "wtp_by_partner_control.png", (0, 10))
    grouped_bar("trust_rating", "Trust rating (0-100)", "V5 Trust by partner type and control condition", "trust_by_partner_control.png", (0, 100))
    grouped_bar("predicted_low_minus_high", "Predicted low return - high return", "V5 Predicted stake threshold by partner", "predicted_low_minus_high.png", (-0.2, 0.45))

    premium = summary["controllability_premium"]
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    vals = [premium[p]["controllable_minus_fixed_high"] or 0 for p in PARTNER_ORDER]
    bars = ax.bar([PARTNER_LABELS[p] for p in PARTNER_ORDER], vals, color=["#235789", "#0f766e", "#64748b"])
    ax.axhline(0, color="#17202a", linewidth=1)
    ax.set_ylabel("WTP controllable - WTP fixed high")
    ax.set_title("V5 Controllability premium")
    for bar, val in zip(bars, vals):
        y = val + 0.05 if val >= 0 else val - 0.05
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{val:.2f}", ha="center", va="bottom" if val >= 0 else "top")
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    fig.savefig(FIG / "controllability_premium.png", dpi=180)
    plt.close(fig)

    chosen = summary["by_partner_control"]
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    bottom = [0.0] * len(PARTNER_ORDER)
    stake_colors = {"low": "#0f766e", "medium": "#64748b", "high": "#b42318"}
    for stake in ["low", "medium", "high"]:
        vals = []
        for partner in PARTNER_ORDER:
            cell = chosen.get(f"{partner} / controllable_stake", {})
            counts = cell.get("chosen_stake_counts", {})
            total = sum(counts.values()) or 1
            vals.append(counts.get(stake, 0) / total)
        ax.bar([PARTNER_LABELS[p] for p in PARTNER_ORDER], vals, bottom=bottom, label=stake, color=stake_colors[stake])
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylim(0, 1)
    ax.set_ylabel("Share of controllable trials")
    ax.set_title("V5 Chosen stake when stake is controllable")
    ax.legend(ncols=3)
    fig.tight_layout()
    fig.savefig(FIG / "chosen_stake_distribution.png", dpi=180)
    plt.close(fig)


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def make_table(summary: dict) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        for control in CONTROL_ORDER:
            key = f"{partner} / {control}"
            item = summary["by_partner_control"].get(key, {})
            rows.append(
                f"<tr><td>{PARTNER_LABELS[partner]}</td><td>{CONTROL_LABELS[control]}</td>"
                f"<td>{item.get('n_success', 0)}/{item.get('n_total', 0)}</td>"
                f"<td>{fmt(item.get('observed_low_minus_high'))}</td>"
                f"<td>{fmt(item.get('predicted_low_minus_high'))}</td>"
                f"<td>{fmt(item.get('trust_rating'))}</td>"
                f"<td>{fmt(item.get('willingness_to_pay'))}</td>"
                f"<td>{fmt(item.get('investment_fraction'))}</td></tr>"
            )
    return "".join(rows)


def make_report(summary: dict) -> None:
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V5 Controllability Pilot</title>
  <style>
    body {{ font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 34px; color: #17202a; line-height: 1.58; }}
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
  </style>
</head>
<body>
  <h1>V5 Controllability Pilot</h1>
  <p class="note">Question: does the model pay for access to a partner it does not trust when it believes the partner's opportunism is predictable and controllable?</p>
  <div class="grid">
    <div class="card"><span class="metric">{summary['overall']['n_success']}/{summary['overall']['n_total']}</span>successful calls</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['willingness_to_pay'])}</span>mean WTP</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['trust_rating'])}</span>mean trust</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['predicted_low_minus_high'])}</span>mean predicted low-high gap</div>
  </div>
  <h2>Main Figures</h2>
  <img src="figures/wtp_by_partner_control.png" alt="WTP by partner and control">
  <img src="figures/trust_by_partner_control.png" alt="Trust by partner and control">
  <img src="figures/controllability_premium.png" alt="Controllability premium">
  <img src="figures/predicted_low_minus_high.png" alt="Predicted threshold">
  <img src="figures/chosen_stake_distribution.png" alt="Chosen stake distribution">
  <h2>Cells</h2>
  <table>
    <thead><tr><th>Partner</th><th>Control</th><th>N</th><th>Observed low-high</th><th>Predicted low-high</th><th>Trust</th><th>WTP</th><th>Investment fraction</th></tr></thead>
    <tbody>{make_table(summary)}</tbody>
  </table>
</body>
</html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")


def main() -> None:
    rows = load_results()
    summary = {
        "overall": aggregate(rows),
        "by_partner": {k: aggregate(v) for k, v in sorted(grouped(rows, ("partner_type",)).items())},
        "by_control": {k: aggregate(v) for k, v in sorted(grouped(rows, ("control_condition",)).items())},
        "by_partner_control": {k: aggregate(v) for k, v in sorted(grouped(rows, ("partner_type", "control_condition")).items())},
        "errors": [r["error"] for r in rows if r.get("error")],
    }
    summary["controllability_premium"] = controllability_premium(summary)
    save_path = OUT / "summary.json"
    save_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    make_plots(summary)
    make_report(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
