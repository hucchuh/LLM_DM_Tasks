from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"

PARTNER_ORDER = ["honest_beneficial", "honest_costly", "dishonest_beneficial", "dishonest_costly"]
MODE_ORDER = ["sequential", "batch"]
PARTNER_LABELS = {
    "honest_beneficial": "Honest\nbeneficial",
    "honest_costly": "Honest\ncostly",
    "dishonest_beneficial": "Dishonest\nbeneficial",
    "dishonest_costly": "Dishonest\ncostly",
}
MODE_LABELS = {"sequential": "Sequential", "batch": "Batch"}
COLORS = {"sequential": "#0f766e", "batch": "#64748b"}


def read_json(path: Path) -> list[dict]:
    if not path.exists():
        alt = OUT / "results_partial.json"
        return json.loads(alt.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def ok(rows: list[dict]) -> list[dict]:
    return [row for row in rows if not row.get("error") and row.get("metrics")]


def avg(values: list) -> float | None:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    return round(mean(vals), 3)


def sd(values: list) -> float | None:
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return None
    return round(pstdev(vals), 3)


def aggregate(rows: list[dict]) -> dict:
    good = ok(rows)

    def metric(key: str) -> list:
        return [row["metrics"].get(key) for row in good if row["metrics"].get(key) is not None]

    return {
        "n_total": len(rows),
        "n_success": len(good),
        "observed_honesty_rate": avg([r.get("observed_honesty_rate") for r in good]),
        "observed_recommendation_win_rate": avg([r.get("observed_recommendation_win_rate") for r in good]),
        "trust_rating": avg(metric("trust_rating")),
        "trust_rating_sd": sd(metric("trust_rating")),
        "willingness_to_pay": avg(metric("willingness_to_pay")),
        "willingness_to_pay_sd": sd(metric("willingness_to_pay")),
        "investment": avg(metric("investment")),
        "expected_return_tokens": avg(metric("expected_return_tokens")),
        "perceived_honesty": avg(metric("perceived_honesty")),
        "perceived_helpfulness": avg(metric("perceived_helpfulness")),
        "actual_choice_win_rate": avg(metric("actual_choice_win_rate")),
        "follow_recommendation_rate": avg(metric("follow_recommendation_rate")),
        "n_api_calls": sum(row.get("n_api_calls", 0) for row in good),
    }


def grouped(rows: list[dict], keys: tuple[str, ...]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        out[" / ".join(str(row.get(k)) for k in keys)].append(row)
    return out


def make_summary(rows: list[dict]) -> dict:
    return {
        "overall": aggregate(rows),
        "by_partner": {k: aggregate(v) for k, v in sorted(grouped(rows, ("partner_type",)).items())},
        "by_mode": {k: aggregate(v) for k, v in sorted(grouped(rows, ("presentation_mode",)).items())},
        "by_partner_mode": {k: aggregate(v) for k, v in sorted(grouped(rows, ("partner_type", "presentation_mode")).items())},
        "errors": [row.get("error") for row in rows if row.get("error")],
    }


def grouped_bar(summary: dict, metric: str, ylabel: str, title: str, filename: str, ylim: tuple[float, float]) -> None:
    cells = summary["by_partner_mode"]
    x = list(range(len(PARTNER_ORDER)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    for i, mode in enumerate(MODE_ORDER):
        vals = [
            cells.get(f"{partner} / {mode}", {}).get(metric) or 0
            for partner in PARTNER_ORDER
        ]
        pos = [p + (i - 0.5) * width for p in x]
        bars = ax.bar(pos, vals, width=width, label=MODE_LABELS[mode], color=COLORS[mode])
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, val + (ylim[1] - ylim[0]) * 0.015, f"{val:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, [PARTNER_LABELS[p] for p in PARTNER_ORDER])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(*ylim)
    ax.legend(ncols=2)
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(FIG / filename, dpi=180)
    plt.close(fig)


def make_plots(summary: dict) -> None:
    FIG.mkdir(exist_ok=True)
    grouped_bar(summary, "trust_rating", "Trust rating (0-100)", "V6 final trust by partner type", "trust_by_partner_mode.png", (0, 100))
    grouped_bar(summary, "willingness_to_pay", "WTP (0-10)", "V6 willingness to pay by partner type", "wtp_by_partner_mode.png", (0, 10))
    grouped_bar(summary, "investment", "Investment (0-10)", "V6 investment by partner type", "investment_by_partner_mode.png", (0, 10))
    grouped_bar(summary, "perceived_honesty", "Perceived honesty (0-100)", "V6 perceived honesty manipulation check", "perceived_honesty_by_partner_mode.png", (0, 100))
    grouped_bar(summary, "perceived_helpfulness", "Perceived helpfulness (0-100)", "V6 perceived helpfulness manipulation check", "perceived_helpfulness_by_partner_mode.png", (0, 100))


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(v)


def table(summary: dict) -> str:
    rows = []
    cells = summary["by_partner_mode"]
    for partner in PARTNER_ORDER:
        for mode in MODE_ORDER:
            item = cells.get(f"{partner} / {mode}", {})
            rows.append(
                "<tr>"
                f"<td>{partner}</td><td>{mode}</td>"
                f"<td class='num'>{item.get('n_success', 0)}/{item.get('n_total', 0)}</td>"
                f"<td class='num'>{fmt(item.get('observed_honesty_rate'))}</td>"
                f"<td class='num'>{fmt(item.get('observed_recommendation_win_rate'))}</td>"
                f"<td class='num'>{fmt(item.get('trust_rating'))}</td>"
                f"<td class='num'>{fmt(item.get('willingness_to_pay'))}</td>"
                f"<td class='num'>{fmt(item.get('investment'))}</td>"
                f"<td class='num'>{fmt(item.get('perceived_honesty'))}</td>"
                f"<td class='num'>{fmt(item.get('perceived_helpfulness'))}</td>"
                f"<td class='num'>{fmt(item.get('actual_choice_win_rate'))}</td>"
                "</tr>"
            )
    return "\n".join(rows)


def make_report(summary: dict) -> None:
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V6 Advice-to-Trust Transfer</title>
  <style>
    body {{ font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 32px; color: #17202a; line-height: 1.62; }}
    h1 {{ margin-bottom: 6px; }}
    h2 {{ margin-top: 30px; }}
    .lead {{ max-width: 980px; color: #526071; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 18px 0; }}
    .card {{ border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; background: #f8fafc; }}
    .metric {{ display:block; font-size: 28px; font-weight: 750; color: #235789; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d8dee6; padding: 8px 9px; text-align: left; }}
    th {{ background: #eef2f7; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    figure {{ margin: 22px 0; border: 1px solid #d8dee6; border-radius: 8px; padding: 12px; }}
    img {{ width: 100%; display: block; }}
    figcaption {{ margin-top: 10px; color: #526071; }}
  </style>
</head>
<body>
  <h1>V6 Advice-to-Trust Transfer</h1>
  <p class="lead">同一个 partner 先在信息建议任务中建立 honesty/helpfulness 声誉，再进入 trust/WTP 决策。核心看 social trust 和 willingness to pay 是否可分离。</p>
  <div class="grid">
    <div class="card"><span class="metric">{summary['overall']['n_success']}/{summary['overall']['n_total']}</span>successful runs</div>
    <div class="card"><span class="metric">{summary['overall']['n_api_calls']}</span>API calls parsed</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['trust_rating'])}</span>mean trust</div>
    <div class="card"><span class="metric">{fmt(summary['overall']['willingness_to_pay'])}</span>mean WTP</div>
  </div>

  <h2>Figures</h2>
  <figure><img src="figures/trust_by_partner_mode.png"><figcaption>Trust rating should track honesty if the model forms social trust representation.</figcaption></figure>
  <figure><img src="figures/wtp_by_partner_mode.png"><figcaption>WTP may track reward/helpfulness more than pure honesty, which would support dissociation.</figcaption></figure>
  <figure><img src="figures/investment_by_partner_mode.png"><figcaption>Investment is the final costly behavioral decision in the one-shot trust game.</figcaption></figure>
  <figure><img src="figures/perceived_honesty_by_partner_mode.png"><figcaption>Manipulation check: the model's explicit perceived honesty should separate honest and dishonest partners.</figcaption></figure>
  <figure><img src="figures/perceived_helpfulness_by_partner_mode.png"><figcaption>Manipulation check: perceived helpfulness should separate beneficial and costly recommendation histories.</figcaption></figure>

  <h2>Cell Summary</h2>
  <table>
    <thead>
      <tr><th>Partner</th><th>Mode</th><th>N</th><th>Honesty</th><th>Rec win</th><th>Trust</th><th>WTP</th><th>Investment</th><th>Perceived honesty</th><th>Perceived helpfulness</th><th>Actual win</th></tr>
    </thead>
    <tbody>{table(summary)}</tbody>
  </table>
</body>
</html>"""
    (OUT / "report.html").write_text(html, encoding="utf-8")


def main() -> None:
    rows = read_json(OUT / "results.json")
    summary = make_summary(rows)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    make_plots(summary)
    make_report(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
