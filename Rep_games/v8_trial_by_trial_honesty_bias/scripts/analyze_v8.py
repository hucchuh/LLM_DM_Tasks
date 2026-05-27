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

PARTNER_ORDER = ["high_honesty_matched_return", "low_honesty_matched_return"]
MODE_ORDER = ["sequential_trial", "evidence_only_trial"]
PARTNER_LABELS = {
    "high_honesty_matched_return": "高诚实",
    "low_honesty_matched_return": "低诚实",
}
MODE_LABELS = {
    "sequential_trial": "连续对话",
    "evidence_only_trial": "独立证据",
}


def load_results() -> list[dict[str, Any]]:
    if not RESULTS.exists():
        raise SystemExit(f"Missing results file: {RESULTS}")
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def flatten_trials(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat = []
    for row in rows:
        if row.get("error"):
            continue
        for trial in row.get("trial_results", []):
            flat.append(
                {
                    "run_id": row["run_id"],
                    "partner_type": row["partner_type"],
                    "presentation_mode": row["presentation_mode"],
                    "seed_index": row["seed_index"],
                    "trial": trial["trial"],
                    "investment": float(trial["investment"]),
                    "statement_true": bool(trial["statement_true"]),
                    "return_rate": float(trial["return_rate"]),
                    "returned_tokens": float(trial["returned_tokens"]),
                    "net_gain_from_investment": float(trial["net_gain_from_investment"]),
                    "trial_payoff": float(10 - trial["investment"] + trial["returned_tokens"]),
                    "cumulative_truth_rate_after": float(trial["cumulative_truth_rate_after"]),
                    "cumulative_return_rate_after": float(trial["cumulative_return_rate_after"]),
                }
            )
    return flat


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return round(stats.stdev(values), 3)


def summarize_trials(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n_trials": len(rows),
        "mean_investment": mean([row["investment"] for row in rows]),
        "sd_investment": sd([row["investment"] for row in rows]),
        "truth_rate": mean([1.0 if row["statement_true"] else 0.0 for row in rows]),
        "mean_return_rate": mean([row["return_rate"] for row in rows]),
        "mean_returned_tokens": mean([row["returned_tokens"] for row in rows]),
        "mean_net_gain": mean([row["net_gain_from_investment"] for row in rows]),
        "mean_trial_payoff": mean([row["trial_payoff"] for row in rows]),
    }


def summarize_runs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if not row.get("error")]
    run_means = []
    run_total_payoffs = []
    run_mean_trial_payoffs = []
    for row in successful:
        investments = [float(trial["investment"]) for trial in row.get("trial_results", [])]
        if investments:
            run_means.append(sum(investments) / len(investments))
        trial_payoffs = [float(10 - trial["investment"] + trial["returned_tokens"]) for trial in row.get("trial_results", [])]
        if trial_payoffs:
            run_total_payoffs.append(sum(trial_payoffs))
            run_mean_trial_payoffs.append(sum(trial_payoffs) / len(trial_payoffs))
    return {
        "n_total": len(rows),
        "n_success": len(successful),
        "mean_run_investment": mean(run_means),
        "sd_run_investment": sd(run_means),
        "mean_run_total_payoff": mean(run_total_payoffs),
        "sd_run_total_payoff": sd(run_total_payoffs),
        "mean_run_trial_payoff": mean(run_mean_trial_payoffs),
        "sd_run_trial_payoff": sd(run_mean_trial_payoffs),
    }


def make_summary(rows: list[dict[str, Any]], flat: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "overall_runs": summarize_runs(rows),
        "overall_trials": summarize_trials(flat),
        "by_partner": {},
        "by_mode": {},
        "by_partner_mode": {},
        "by_trial": {},
        "contrasts": {},
    }
    for partner in PARTNER_ORDER:
        partner_rows = [row for row in flat if row["partner_type"] == partner]
        summary["by_partner"][partner] = summarize_trials(partner_rows)
    for mode in MODE_ORDER:
        mode_rows = [row for row in flat if row["presentation_mode"] == mode]
        summary["by_mode"][mode] = summarize_trials(mode_rows)
    for partner in PARTNER_ORDER:
        for mode in MODE_ORDER:
            key = f"{partner} / {mode}"
            cell_rows = [row for row in flat if row["partner_type"] == partner and row["presentation_mode"] == mode]
            run_rows = [row for row in rows if row["partner_type"] == partner and row["presentation_mode"] == mode]
            summary["by_partner_mode"][key] = {
                **summarize_runs(run_rows),
                **summarize_trials(cell_rows),
            }
    for trial in sorted({row["trial"] for row in flat}):
        summary["by_trial"][str(trial)] = {}
        for partner in PARTNER_ORDER:
            for mode in MODE_ORDER:
                key = f"{partner} / {mode}"
                cell_rows = [
                    row
                    for row in flat
                    if row["trial"] == trial and row["partner_type"] == partner and row["presentation_mode"] == mode
                ]
                summary["by_trial"][str(trial)][key] = summarize_trials(cell_rows)

    high = summary["by_partner"]["high_honesty_matched_return"]["mean_investment"]
    low = summary["by_partner"]["low_honesty_matched_return"]["mean_investment"]
    if high is not None and low is not None:
        summary["contrasts"]["overall_high_minus_low_investment"] = round(high - low, 3)
    for mode in MODE_ORDER:
        h = summary["by_partner_mode"][f"high_honesty_matched_return / {mode}"]["mean_investment"]
        l = summary["by_partner_mode"][f"low_honesty_matched_return / {mode}"]["mean_investment"]
        if h is not None and l is not None:
            summary["contrasts"][f"{mode}_high_minus_low_investment"] = round(h - l, 3)
        h_payoff = summary["by_partner_mode"][f"high_honesty_matched_return / {mode}"]["mean_trial_payoff"]
        l_payoff = summary["by_partner_mode"][f"low_honesty_matched_return / {mode}"]["mean_trial_payoff"]
        if h_payoff is not None and l_payoff is not None:
            summary["contrasts"][f"{mode}_high_minus_low_trial_payoff"] = round(h_payoff - l_payoff, 3)
        h_total = summary["by_partner_mode"][f"high_honesty_matched_return / {mode}"]["mean_run_total_payoff"]
        l_total = summary["by_partner_mode"][f"low_honesty_matched_return / {mode}"]["mean_run_total_payoff"]
        if h_total is not None and l_total is not None:
            summary["contrasts"][f"{mode}_high_minus_low_run_total_payoff"] = round(h_total - l_total, 3)
    return summary


def setup_plot() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 180


def plot_bar(summary: dict[str, Any]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    values = [
        summary["by_partner_mode"][f"{partner} / sequential_trial"]["mean_investment"] or 0
        for partner in PARTNER_ORDER
    ]
    bars = ax.bar(range(len(PARTNER_ORDER)), values, color=["#2f78b7", "#d95b52"], width=0.55)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom", fontsize=13)
    ax.set_xticks(range(len(PARTNER_ORDER)))
    ax.set_xticklabels([PARTNER_LABELS[p] for p in PARTNER_ORDER], fontsize=13)
    ax.set_ylabel("平均投资额 (0-10)", fontsize=13)
    ax.set_title("V8 主结果：连续逐轮互动中的平均投资", fontsize=15)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "mean_investment_by_condition.png", bbox_inches="tight")
    plt.close(fig)


def plot_trial_lines(summary: dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6))
    trials = [int(item) for item in summary["by_trial"].keys()]
    styles = {
        "high_honesty_matched_return / sequential_trial": ("#1f77b4", "-", "高诚实/连续对话"),
        "low_honesty_matched_return / sequential_trial": ("#d62728", "-", "低诚实/连续对话"),
    }
    for key, (color, line_style, label) in styles.items():
        values = [summary["by_trial"][str(trial)][key]["mean_investment"] for trial in trials]
        ax.plot(trials, values, color=color, linestyle=line_style, marker="o", linewidth=2, label=label)
    ax.set_xlabel("Trial", fontsize=13)
    ax.set_ylabel("平均投资额 (0-10)", fontsize=13)
    ax.set_title("逐轮投资轨迹", fontsize=15)
    ax.set_xticks(trials)
    ax.legend(frameon=False, fontsize=11)
    ax.grid(alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "investment_over_trials.png", bbox_inches="tight")
    plt.close(fig)


def plot_return_check(summary: dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    labels = []
    values = []
    for partner in PARTNER_ORDER:
        key = f"{partner} / sequential_trial"
        labels.append(PARTNER_LABELS[partner])
        values.append(summary["by_partner_mode"][key]["mean_return_rate"] or 0)
    bars = ax.bar(range(len(labels)), values, color=["#6aa6d8", "#e58d85"], width=0.55)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom", fontsize=12)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("平均返还比例", fontsize=13)
    ax.set_title("操纵检查：各条件实际返还政策被匹配", fontsize=15)
    ax.set_ylim(0, max(values) + 0.15)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "return_rate_check.png", bbox_inches="tight")
    plt.close(fig)


def plot_payoff(summary: dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    values = [
        summary["by_partner_mode"][f"{partner} / sequential_trial"]["mean_trial_payoff"] or 0
        for partner in PARTNER_ORDER
    ]
    bars = ax.bar(range(len(PARTNER_ORDER)), values, color=["#2f78b7", "#d95b52"], width=0.55)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom", fontsize=13)
    ax.set_xticks(range(len(PARTNER_ORDER)))
    ax.set_xticklabels([PARTNER_LABELS[p] for p in PARTNER_ORDER], fontsize=13)
    ax.set_ylabel("每轮总收益", fontsize=13)
    ax.set_title("实际 payoff：10 - 投资 + 返还", fontsize=15)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "payoff_by_condition.png", bbox_inches="tight")
    plt.close(fig)


def make_figures(summary: dict[str, Any]) -> None:
    setup_plot()
    plot_bar(summary)
    plot_trial_lines(summary)
    plot_return_check(summary)
    plot_payoff(summary)


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def table_rows(summary: dict[str, Any]) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        key = f"{partner} / sequential_trial"
        item = summary["by_partner_mode"][key]
        rows.append(
            "<tr>"
            f"<td>{PARTNER_LABELS[partner]}</td>"
            f"<td>{fmt(item.get('n_success'))}/{fmt(item.get('n_total'))}</td>"
            f"<td>{fmt(item.get('truth_rate'))}</td>"
            f"<td>{fmt(item.get('mean_return_rate'))}</td>"
            f"<td>{fmt(item.get('mean_investment'))}</td>"
            f"<td>{fmt(item.get('mean_returned_tokens'))}</td>"
            f"<td>{fmt(item.get('mean_net_gain'))}</td>"
            f"<td>{fmt(item.get('mean_trial_payoff'))}</td>"
            f"<td>{fmt(item.get('mean_run_total_payoff'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def write_report(summary: dict[str, Any]) -> None:
    c = summary["contrasts"]
    high_seq = summary["by_partner_mode"]["high_honesty_matched_return / sequential_trial"]
    low_seq = summary["by_partner_mode"]["low_honesty_matched_return / sequential_trial"]
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>V8 逐轮投资中的诚实偏置</title>
  <style>
    body {{ margin: 0; font-family: "Microsoft YaHei", Arial, sans-serif; background: #f6f8fb; color: #162233; }}
    header {{ padding: 44px 56px; background: #173650; color: white; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 30px; }}
    section {{ background: white; border: 1px solid #dbe5ee; border-radius: 8px; padding: 24px; margin: 22px 0; }}
    h1 {{ margin: 0 0 12px; font-size: 36px; }}
    h2 {{ margin: 0 0 14px; font-size: 24px; }}
    p, li {{ font-size: 17px; line-height: 1.7; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
    th, td {{ border-bottom: 1px solid #e4ebf2; padding: 10px; text-align: left; }}
    th {{ background: #eef4f9; }}
    img {{ display: block; width: 100%; max-width: 980px; border: 1px solid #dbe5ee; border-radius: 6px; margin: 18px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .card {{ background: #f8fafc; border: 1px solid #e1e8ef; border-radius: 8px; padding: 16px; }}
    .metric {{ font-size: 31px; font-weight: 800; color: #174a73; }}
    .note {{ color: #43556a; }}
  </style>
</head>
<body>
  <header>
    <h1>V8 逐轮投资中的诚实偏置</h1>
    <p>这版不再让模型看完历史后做一次总结判断，而是每一轮都先做投资，再收到反馈。主任务只问 investment，不问 trust、honesty、WTP 或理由。</p>
  </header>
  <main>
    <section>
      <h2>研究问题</h2>
      <p>如果两个 partner 的实际返还政策完全相同，但一个更常说真话，另一个更常说假话，模型会不会在逐轮投资中把“说真话”当成一种社会信号，从而投更多？</p>
      <p>这里的关键控制是：高诚实和低诚实条件使用同一组返还比例。也就是说，模型看到的实际回报政策被匹配；差异只来自可核验陈述的真伪历史。</p>
    </section>

    <section>
      <h2>核心结果</h2>
      <div class="grid">
        <div class="card"><div class="metric">{fmt(high_seq.get('mean_investment'))}</div><p>高诚实 partner 的平均投资。</p></div>
        <div class="card"><div class="metric">{fmt(low_seq.get('mean_investment'))}</div><p>低诚实 partner 的平均投资。</p></div>
        <div class="card"><div class="metric">{fmt(high_seq.get('mean_return_rate'))} / {fmt(low_seq.get('mean_return_rate'))}</div><p>两组平均返还比例，高诚实 / 低诚实。</p></div>
      </div>
      <p>高诚实条件比低诚实条件平均多投 {fmt(c.get('sequential_trial_high_minus_low_investment'))} 个 token。因为两组平均返还比例都是 {fmt(high_seq.get('mean_return_rate'))}，这个差异不能简单解释为一组更会返还。</p>
      <p>这个投资差异进一步影响了实际收益。这里每轮 payoff 定义为 <strong>10 - investment + returned_tokens</strong>。高诚实条件每轮平均 payoff 为 {fmt(high_seq.get('mean_trial_payoff'))}，低诚实条件为 {fmt(low_seq.get('mean_trial_payoff'))}，差值为 {fmt(c.get('sequential_trial_high_minus_low_trial_payoff'))}。换算到一个 18-trial run，高诚实条件平均总 payoff 为 {fmt(high_seq.get('mean_run_total_payoff'))}，低诚实条件为 {fmt(low_seq.get('mean_run_total_payoff'))}，差值为 {fmt(c.get('sequential_trial_high_minus_low_run_total_payoff'))}。</p>
      <p>因此，V8 的结果不是“低诚实 partner 实际更差”，而是：在返还政策相同且总体正收益的情况下，模型因为不相信低诚实对象而投得更少，最终也少拿了一部分收益。这正是 honesty bias 在行为层面的代价。</p>
    </section>

    <section>
      <h2>条件均值</h2>
      <table>
        <thead><tr><th>诚实条件</th><th>Run</th><th>真实率</th><th>平均返还比例</th><th>平均投资</th><th>平均返还 token</th><th>平均净收益</th><th>每轮总收益</th><th>每 run 总收益</th></tr></thead>
        <tbody>{table_rows(summary)}</tbody>
      </table>
      <p class="note">真实率是实际操纵检查；平均返还比例用于检查 payoff policy 是否匹配。平均净收益 = returned_tokens - investment；每轮总收益 = 10 - investment + returned_tokens。</p>
    </section>

    <section>
      <h2>图示</h2>
      <img src="figures/mean_investment_by_condition.png" alt="Mean investment by condition">
      <p class="note">图 1：四个条件的平均投资额。若高诚实条件更高，说明 honesty 在实际回报匹配时仍影响投资。</p>
      <img src="figures/investment_over_trials.png" alt="Investment over trials">
      <p class="note">图 2：逐轮投资轨迹。这个图用来看 honesty bias 是早期就出现、随证据累积增强，还是被返还反馈抵消。</p>
      <img src="figures/return_rate_check.png" alt="Return rate check">
      <p class="note">图 3：返还比例操纵检查。理论上四个条件应当非常接近，因为 return policy 是 yoked 的。</p>
      <img src="figures/payoff_by_condition.png" alt="Payoff by condition">
      <p class="note">图 4：实际 payoff。低诚实对象的返还政策并不差，但模型投得更少，因此可获得的正收益也更少。</p>
    </section>

    <section>
      <h2>如何解读</h2>
      <p>如果连续对话和独立证据都出现高诚实投资更高，说明模型会把 factual honesty 迁移到实际投资风险暴露上。</p>
      <p>如果只有连续对话出现差异，则可能说明 honesty bias 需要持续互动上下文或自我一致性累积。</p>
      <p>如果只有独立证据出现差异，则可能说明一次次独立总结更容易把真伪历史转成投资策略，而连续互动会被短期回报或前一轮投资锚定。</p>
      <p>如果两者都没有差异，则说明在真正逐轮投资里，模型主要看返还反馈，而不是可核验陈述的诚实程度。</p>
      <p>本轮 API 测试中，evidence-only 条件会诱发 MiniMax-M2.7 长篇推理并频繁无法返回 JSON，因此当前报告只解释完整跑完的连续逐轮互动条件。这个限制本身也提示：独立历史回看更容易让任务变成“找隐藏策略”的题，而连续互动更接近我们想看的行为过程。</p>
    </section>
  </main>
</body>
</html>
"""
    REPORT.write_text(html, encoding="utf-8")


def main() -> None:
    rows = load_results()
    flat = flatten_trials(rows)
    summary = make_summary(rows, flat)
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    make_figures(summary)
    write_report(summary)
    print(f"Wrote {SUMMARY}")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
