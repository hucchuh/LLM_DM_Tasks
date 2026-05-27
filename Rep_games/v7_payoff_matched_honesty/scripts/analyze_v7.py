from __future__ import annotations

import json
import statistics as stats
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
RESULTS = OUT / "results.json"
SUMMARY = OUT / "summary.json"
REPORT = OUT / "report.html"
FIG = OUT / "figures"

PARTNER_ORDER = ["honest_matched", "dishonest_matched"]
MODE_ORDER = ["sequential_observation", "batch_review"]
PARTNER_LABELS = {
    "honest_matched": "诚实但收益匹配",
    "dishonest_matched": "不诚实但收益匹配",
}
MODE_LABELS = {
    "sequential_observation": "逐轮观察",
    "batch_review": "一次性回看",
}

METRICS = [
    "enter_choice",
    "willingness_to_pay",
    "investment",
    "perceived_honesty",
    "perceived_helpfulness",
    "expected_recommendation_win_rate",
    "moral_trust",
]


def load_results() -> list[dict[str, Any]]:
    if not RESULTS.exists():
        raise SystemExit(f"Missing results file: {RESULTS}")
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def metric_value(row: dict[str, Any], key: str) -> float | None:
    if key in {"enter_choice", "willingness_to_pay", "investment"}:
        value = (row.get("main_metrics") or {}).get(key)
    else:
        value = (row.get("probe_metrics") or {}).get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return round(stats.stdev(values), 3)


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if not row.get("error")]
    out: dict[str, Any] = {
        "n_total": len(rows),
        "n_success": len(successful),
    }
    if successful:
        out["observed_honesty_rate"] = mean([float(row["observed_honesty_rate"]) for row in successful])
        out["observed_recommendation_win_rate"] = mean([float(row["observed_recommendation_win_rate"]) for row in successful])

    for key in METRICS:
        values = [value for row in successful if (value := metric_value(row, key)) is not None]
        out[key] = mean(values)
        out[f"{key}_sd"] = sd(values)
    return out


def contrast(summary: dict[str, Any], group: str = "by_partner") -> dict[str, Any]:
    honest = summary[group].get("honest_matched", {})
    dishonest = summary[group].get("dishonest_matched", {})
    result = {}
    for key in METRICS:
        if honest.get(key) is not None and dishonest.get(key) is not None:
            result[f"{key}_honest_minus_dishonest"] = round(honest[key] - dishonest[key], 3)
    return result


def make_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "overall": summarize_group(rows),
        "by_partner": {},
        "by_mode": {},
        "by_partner_mode": {},
    }
    for partner in PARTNER_ORDER:
        summary["by_partner"][partner] = summarize_group([row for row in rows if row["partner_type"] == partner])
    for mode in MODE_ORDER:
        summary["by_mode"][mode] = summarize_group([row for row in rows if row["presentation_mode"] == mode])
    for partner in PARTNER_ORDER:
        for mode in MODE_ORDER:
            key = f"{partner} / {mode}"
            summary["by_partner_mode"][key] = summarize_group(
                [row for row in rows if row["partner_type"] == partner and row["presentation_mode"] == mode]
            )

    summary["honesty_transfer_contrast"] = contrast(summary)
    summary["mode_specific_contrasts"] = {}
    for mode in MODE_ORDER:
        mode_summary = {
            "by_partner": {
                partner: summary["by_partner_mode"][f"{partner} / {mode}"]
                for partner in PARTNER_ORDER
            }
        }
        summary["mode_specific_contrasts"][mode] = contrast(mode_summary)
    return summary


def setup_plot() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 180


def plot_metric(summary: dict[str, Any], metric: str, ylabel: str, filename: str) -> None:
    FIG.mkdir(exist_ok=True)
    x = list(range(len(PARTNER_ORDER)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for i, mode in enumerate(MODE_ORDER):
        values = [summary["by_partner_mode"][f"{partner} / {mode}"].get(metric) or 0 for partner in PARTNER_ORDER]
        pos = [item + (i - 0.5) * width for item in x]
        bars = ax.bar(pos, values, width=width, label=MODE_LABELS[mode])
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([PARTNER_LABELS[p] for p in PARTNER_ORDER])
    ax.set_ylabel(ylabel)
    ax.set_title(metric.replace("_", " ").title())
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / filename, bbox_inches="tight")
    plt.close(fig)


def make_figures(summary: dict[str, Any]) -> None:
    setup_plot()
    plot_metric(summary, "willingness_to_pay", "WTP (0-10)", "wtp_by_honesty_mode.png")
    plot_metric(summary, "investment", "Investment (0-10)", "investment_by_honesty_mode.png")
    plot_metric(summary, "perceived_honesty", "Perceived honesty (0-100)", "perceived_honesty_by_mode.png")
    plot_metric(summary, "perceived_helpfulness", "Perceived helpfulness (0-100)", "perceived_helpfulness_by_mode.png")


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def rows_for_partner(summary: dict[str, Any]) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        item = summary["by_partner"][partner]
        rows.append(
            "<tr>"
            f"<td>{PARTNER_LABELS[partner]}</td>"
            f"<td>{item['n_success']}/{item['n_total']}</td>"
            f"<td>{fmt(item.get('observed_honesty_rate'))}</td>"
            f"<td>{fmt(item.get('observed_recommendation_win_rate'))}</td>"
            f"<td>{fmt(item.get('willingness_to_pay'))}</td>"
            f"<td>{fmt(item.get('investment'))}</td>"
            f"<td>{fmt(item.get('perceived_honesty'))}</td>"
            f"<td>{fmt(item.get('perceived_helpfulness'))}</td>"
            f"<td>{fmt(item.get('moral_trust'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def rows_for_mode(summary: dict[str, Any]) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        for mode in MODE_ORDER:
            item = summary["by_partner_mode"][f"{partner} / {mode}"]
            rows.append(
                "<tr>"
                f"<td>{PARTNER_LABELS[partner]}</td>"
                f"<td>{MODE_LABELS[mode]}</td>"
                f"<td>{item['n_success']}/{item['n_total']}</td>"
                f"<td>{fmt(item.get('willingness_to_pay'))}</td>"
                f"<td>{fmt(item.get('investment'))}</td>"
                f"<td>{fmt(item.get('perceived_honesty'))}</td>"
                f"<td>{fmt(item.get('perceived_helpfulness'))}</td>"
                f"<td>{fmt(item.get('moral_trust'))}</td>"
                "</tr>"
            )
    return "\n".join(rows)


def write_report(summary: dict[str, Any]) -> None:
    contrast_item = summary["honesty_transfer_contrast"]
    seq = summary["mode_specific_contrasts"]["sequential_observation"]
    batch = summary["mode_specific_contrasts"]["batch_review"]
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V7 收益匹配后的诚实迁移实验</title>
  <style>
    body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 0; background: #f6f8fb; color: #142033; }}
    header {{ background: #14324a; color: white; padding: 44px 54px; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px; }}
    section {{ background: white; border: 1px solid #dce5ee; border-radius: 8px; margin: 22px 0; padding: 24px; }}
    h1 {{ margin: 0 0 12px; font-size: 36px; }}
    h2 {{ margin: 0 0 16px; font-size: 24px; }}
    p, li {{ font-size: 17px; line-height: 1.65; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
    th, td {{ border-bottom: 1px solid #e3e9f1; padding: 10px; text-align: left; }}
    th {{ background: #edf3f8; }}
    img {{ width: 100%; max-width: 920px; display: block; border: 1px solid #dce5ee; border-radius: 6px; margin: 18px 0; }}
    code {{ background: #eef2f6; padding: 1px 5px; border-radius: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .card {{ background: #f8fafc; border: 1px solid #e1e8ef; border-radius: 8px; padding: 16px; }}
    .metric {{ font-size: 30px; font-weight: 800; color: #174a73; }}
    .note {{ color: #405366; }}
  </style>
</head>
<body>
  <header>
    <h1>V7 收益匹配后的诚实迁移实验</h1>
    <p>核心问题：当建议带来的实际收益被严格匹配之后，模型是否还会因为一个对象更诚实，而更愿意付费、进入互动、投入更多资源？</p>
  </header>
  <main>
    <section>
      <h2>为什么做 V7</h2>
      <p>V6 已经证明模型可以把“这个人说真话”和“这个人让我赚钱”分开。但那个设计里 honesty 和 payoff 是两个很清楚的变量，容易被模型当成一道分类题。V7 因此把两类对象的建议收益固定为完全一样：12 轮里都只有 6 次建议会赢。唯一改变的是事实陈述是否诚实。</p>
      <p>这样可以问一个更干净的问题：如果一个人并没有让模型赚更多钱，只是更诚实，模型会不会把这种诚实迁移到后续的付费和投资行为上？</p>
    </section>

    <section>
      <h2>实验设计</h2>
      <p>每个 run 先看到同一个 partner 的 12 轮信息建议记录。每轮包含：partner 声称自己看到某张牌的数值、给出左右选择建议，随后反馈真实牌面、陈述是否真实、建议是否会赢。</p>
      <p>两个条件的建议收益完全相同，都是 6/12 次建议会赢；区别只在事实陈述：诚实条件为 9/12 次真实，不诚实条件为 3/12 次真实。之后模型进入一次新的投资互动，需要输出是否进入、最多愿意支付多少入场费、以及投入多少 token。honesty 和 helpfulness 只在之后的 probe 中测量，不在主决策里询问。</p>
    </section>

    <section>
      <h2>总体结果</h2>
      <table>
        <thead><tr><th>对象</th><th>N</th><th>实际诚实率</th><th>建议胜率</th><th>WTP</th><th>投资额</th><th>感知诚实</th><th>感知有用</th><th>道德信任</th></tr></thead>
        <tbody>{rows_for_partner(summary)}</tbody>
      </table>
      <p class="note">操纵检查是干净的：模型把诚实对象评为约 75 分，不诚实对象约 24.8 分；但两组的 perceived helpfulness 几乎一样，约 50 分，expected recommendation win rate 也都是 0.5。</p>
    </section>

    <section>
      <h2>主要对比</h2>
      <div class="grid">
        <div class="card"><div class="metric">{fmt(contrast_item.get('willingness_to_pay_honest_minus_dishonest'))}</div><p>诚实对象相对不诚实对象的 WTP 提升。</p></div>
        <div class="card"><div class="metric">{fmt(contrast_item.get('investment_honest_minus_dishonest'))}</div><p>诚实对象相对不诚实对象的投资额提升。</p></div>
        <div class="card"><div class="metric">{fmt(contrast_item.get('perceived_honesty_honest_minus_dishonest'))}</div><p>操纵检查中的感知诚实差异。</p></div>
      </div>
      <p>总体上，诚实对象获得更高的道德信任，也获得更高的 WTP 和投资额。这说明在收益完全匹配时，honesty 并没有被模型视为纯粹无关的道德标签，而是会部分迁移到后续的 costly reliance。</p>
      <p>但这个迁移并不稳定地出现在所有呈现方式中。逐轮观察时，诚实对象的 WTP 只高 {fmt(seq.get('willingness_to_pay_honest_minus_dishonest'))}，投资额反而低 {fmt(abs(seq.get('investment_honest_minus_dishonest') or 0))}；一次性回看时，诚实对象的 WTP 高 {fmt(batch.get('willingness_to_pay_honest_minus_dishonest'))}，投资额高 {fmt(batch.get('investment_honest_minus_dishonest'))}。这提示“信息如何进入上下文”本身会改变模型把社会评价转化为行动的方式。</p>
    </section>

    <section>
      <h2>图示结果</h2>
      <img src="figures/wtp_by_honesty_mode.png" alt="WTP">
      <p class="note">图 1：WTP。总体上诚实对象更高；batch 条件下差异更大，逐轮条件下差异较小。</p>
      <img src="figures/investment_by_honesty_mode.png" alt="Investment">
      <p class="note">图 2：投资额。最关键的是逐轮条件与 batch 条件方向不同：逐轮时模型虽然认为诚实对象更可信，但投资额没有相应提高；batch 时投资额明显向诚实对象倾斜。</p>
      <img src="figures/perceived_honesty_by_mode.png" alt="Perceived honesty">
      <p class="note">图 3：感知诚实。两种呈现方式下操纵都非常强，说明模型确实提取了 honesty。</p>
      <img src="figures/perceived_helpfulness_by_mode.png" alt="Perceived helpfulness">
      <p class="note">图 4：感知有用性。两组几乎完全相同，说明 payoff matching 成功，不是因为诚实对象显得更能带来收益。</p>
    </section>

    <section>
      <h2>呈现方式拆分</h2>
      <table>
        <thead><tr><th>对象</th><th>呈现方式</th><th>N</th><th>WTP</th><th>投资额</th><th>感知诚实</th><th>感知有用</th><th>道德信任</th></tr></thead>
        <tbody>{rows_for_mode(summary)}</tbody>
      </table>
      <p>这个拆分可能是 V7 最值得继续追的地方。batch 更像在做总结判断，honesty 更容易进入最终决策；sequential 更像真实互动，模型持续接收反馈，但最后付费和投资没有完全跟随 moral trust。这给下一版留下了一个清楚问题：模型是如何在连续互动中把“我认为你诚实”和“我愿意承担风险”连接或分离的？</p>
    </section>
  </main>
</body>
</html>
"""
    REPORT.write_text(html, encoding="utf-8")


def main() -> None:
    rows = load_results()
    summary = make_summary(rows)
    write_json = lambda path, data: path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_json(SUMMARY, summary)
    make_figures(summary)
    write_report(summary)
    print(f"Wrote {SUMMARY}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
