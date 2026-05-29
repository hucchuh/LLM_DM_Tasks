from __future__ import annotations

import csv
import html
import itertools
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "sessions" / "expanded_30seeds"
FIG = SESSION / "figures"


def read_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for key in ["run_id", "seed_index", "choice_trial", "investment", "payoff"]:
                if key in row and row[key] != "":
                    row[key] = float(row[key]) if key in {"investment", "payoff"} else int(float(row[key]))
            rows.append(row)
    return rows


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def m(xs: list[float]) -> float:
    return mean(xs) if xs else float("nan")


def sem(xs: list[float]) -> float:
    return stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float("nan")


def ci95_halfwidth(xs: list[float]) -> float:
    return 1.96 * sem(xs) if len(xs) > 1 else 0.0


def summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": round(m(values), 3),
        "sd": round(stdev(values), 3) if len(values) > 1 else None,
        "sem": round(sem(values), 3) if len(values) > 1 else None,
        "ci95_low": round(m(values) - ci95_halfwidth(values), 3) if values else None,
        "ci95_high": round(m(values) + ci95_halfwidth(values), 3) if values else None,
    }


def session_phase_values(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[float]]:
    buckets: dict[tuple[str, str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        buckets[
            (
                row["midpoint_message"],
                row["honesty_level"],
                row["phase"],
                int(row["run_id"]),
            )
        ].append(float(row["investment"]))
    out: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for (midpoint, honesty, phase, _run), vals in buckets.items():
        out[(midpoint, honesty, phase)].append(m(vals))
    return out


def trial_values(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], list[float]]:
    out: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        out[(row["midpoint_message"], row["honesty_level"], int(row["choice_trial"]))].append(float(row["investment"]))
    return out


def seed_gap_values(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[float]]:
    out: dict[tuple[str, str], list[float]] = defaultdict(list)
    seeds = sorted({int(row["seed_index"]) for row in rows})
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            for seed in seeds:
                high = [
                    float(row["investment"])
                    for row in rows
                    if int(row["seed_index"]) == seed
                    and row["midpoint_message"] == midpoint
                    and row["honesty_level"] == "high"
                    and row["phase"] == phase
                ]
                low = [
                    float(row["investment"])
                    for row in rows
                    if int(row["seed_index"]) == seed
                    and row["midpoint_message"] == midpoint
                    and row["honesty_level"] == "low"
                    and row["phase"] == phase
                ]
                if high and low:
                    out[(midpoint, phase)].append(m(low) - m(high))
    return out


def seed_did_values(rows: list[dict[str, Any]]) -> list[float]:
    gaps = seed_gap_values(rows)
    did = []
    for idx in range(len(gaps[("neutral_reminder", "pre")])):
        neutral_change = gaps[("neutral_reminder", "post")][idx] - gaps[("neutral_reminder", "pre")][idx]
        orth_change = (
            gaps[("orthogonality_disclosure", "post")][idx]
            - gaps[("orthogonality_disclosure", "pre")][idx]
        )
        did.append(orth_change - neutral_change)
    return did


def signflip_p(values: list[float], sims: int = 200000) -> float:
    observed = abs(m(values))
    if len(values) <= 18:
        total = 0
        count = 0
        for signs in itertools.product([-1, 1], repeat=len(values)):
            total += 1
            stat = abs(m([value * sign for value, sign in zip(values, signs)]))
            if stat >= observed - 1e-12:
                count += 1
        return count / total
    rng = random.Random(20260529)
    count = 0
    for _ in range(sims):
        stat = abs(m([value * (1 if rng.random() < 0.5 else -1) for value in values]))
        if stat >= observed - 1e-12:
            count += 1
    return count / sims


def normal_p(values: list[float]) -> float:
    z = m(values) / sem(values)
    cdf = 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))
    return 2 * (1 - cdf)


def html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>暂无结果。</p>"
    cols = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(col)}</th>" for col in cols)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in cols) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def make_plots(rows: list[dict[str, Any]], probe_rows: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    colors = {"high": "#2f6f9f", "low": "#d95f59"}
    tv = trial_values(rows)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharey=True)
    for ax, midpoint in zip(axes, ["neutral_reminder", "orthogonality_disclosure"]):
        for honesty in ["high", "low"]:
            xs, ys, yerr = [], [], []
            for trial in range(1, 13):
                vals = tv[(midpoint, honesty, trial)]
                xs.append(trial)
                ys.append(m(vals))
                yerr.append(ci95_halfwidth(vals))
            ax.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, linewidth=2.5, color=colors[honesty], label=honesty)
        ax.axvline(6.5, color="#4b5563", linestyle="--", linewidth=1.5)
        ax.set_title(midpoint.replace("_", " "), fontsize=14)
        ax.set_xlabel("Choice round", fontsize=12)
        ax.set_ylim(0, 10)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Mean investment with 95% CI", fontsize=12)
    axes[1].legend(frameon=False)
    fig.suptitle("Trial-by-trial investment, error bars across LLM sessions", fontsize=16)
    fig.tight_layout()
    fig.savefig(FIG / "stats_investment_trajectory_ci.png", dpi=190)
    plt.close(fig)

    phase_values = session_phase_values(rows)
    labels, means, errs, bar_colors = [], [], [], []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            for honesty in ["high", "low"]:
                vals = phase_values[(midpoint, honesty, phase)]
                labels.append(f"{midpoint.replace('_', ' ')}\n{phase}\n{honesty}")
                means.append(m(vals))
                errs.append(ci95_halfwidth(vals))
                bar_colors.append(colors[honesty])
    fig, ax = plt.subplots(figsize=(14, 5.8))
    ax.bar(range(len(labels)), means, yerr=errs, capsize=4, color=bar_colors, alpha=0.9)
    ax.set_xticks(range(len(labels)), labels, rotation=22, ha="right")
    ax.set_ylabel("Session mean investment with 95% CI", fontsize=12)
    ax.set_title("Phase-level investment by condition", fontsize=16)
    ax.set_ylim(0, 8)
    fig.tight_layout()
    fig.savefig(FIG / "stats_phase_means_ci.png", dpi=190)
    plt.close(fig)

    gaps = seed_gap_values(rows)
    labels, means, errs, colors_gap = [], [], [], []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            vals = gaps[(midpoint, phase)]
            labels.append(f"{midpoint.replace('_', ' ')}\n{phase}")
            means.append(m(vals))
            errs.append(ci95_halfwidth(vals))
            colors_gap.append("#7a8f3a" if midpoint == "neutral_reminder" else "#9b5de5")
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    ax.bar(labels, means, yerr=errs, capsize=4, color=colors_gap)
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_ylabel("Low honesty - high honesty investment with 95% CI", fontsize=12)
    ax.set_title("Matched-session honesty gap", fontsize=16)
    fig.tight_layout()
    fig.savefig(FIG / "stats_honesty_gap_ci.png", dpi=190)
    plt.close(fig)

    if probe_rows:
        metrics = ["moral_trust", "expected_return_rate", "truth_return_link", "controllability"]
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        axes = axes.flatten()
        for ax, metric in zip(axes, metrics):
            labels, means, errs, bar_colors = [], [], [], []
            for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
                for honesty in ["high", "low"]:
                    vals = [
                        float(row[metric])
                        for row in probe_rows
                        if row["midpoint_message"] == midpoint and row["honesty_level"] == honesty and row.get(metric) not in {"", None}
                    ]
                    labels.append(f"{midpoint.replace('_', ' ')}\n{honesty}")
                    means.append(m(vals))
                    errs.append(ci95_halfwidth(vals))
                    bar_colors.append(colors[honesty])
            ax.bar(range(len(labels)), means, yerr=errs, capsize=4, color=bar_colors)
            ax.set_xticks(range(len(labels)), labels, rotation=20, ha="right", fontsize=8)
            ax.set_title(metric)
            if metric != "expected_return_rate":
                ax.set_ylim(0, 100)
            else:
                ax.set_ylim(0, 1)
        fig.suptitle("Final probe with 95% CI across complete sessions", fontsize=16)
        fig.tight_layout()
        fig.savefig(FIG / "stats_final_probe_ci.png", dpi=190)
        plt.close(fig)


def main() -> None:
    rows = read_csv(SESSION / "trial_level_data.csv")
    probe_rows = read_csv(SESSION / "final_probe_data.csv") if (SESSION / "final_probe_data.csv").exists() else []
    summary_json = read_json(SESSION / "summary.json", {})
    power = read_json(SESSION / "power_analysis.json", {})
    make_plots(rows, probe_rows)

    phase_values = session_phase_values(rows)
    phase_table = []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for honesty in ["high", "low"]:
            for phase in ["pre", "post"]:
                row = {
                    "midpoint": midpoint,
                    "honesty": honesty,
                    "phase": phase,
                    **summary(phase_values[(midpoint, honesty, phase)]),
                }
                phase_table.append(row)

    gap_table = []
    gaps = seed_gap_values(rows)
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        pre = gaps[(midpoint, "pre")]
        post = gaps[(midpoint, "post")]
        change = [b - a for a, b in zip(pre, post)]
        gap_table.append(
            {
                "midpoint": midpoint,
                "pre_low_minus_high": round(m(pre), 3),
                "post_low_minus_high": round(m(post), 3),
                "post_minus_pre": round(m(change), 3),
                "post_minus_pre_ci95": f"[{round(m(change)-ci95_halfwidth(change),3)}, {round(m(change)+ci95_halfwidth(change),3)}]",
            }
        )
    did = seed_did_values(rows)
    did_summary = {
        "n_matched_sessions": len(did),
        "mean_DID": round(m(did), 3),
        "sd": round(stdev(did), 3),
        "sem": round(sem(did), 3),
        "normal_p": round(normal_p(did), 4),
        "signflip_p": round(signflip_p(did), 4),
        "ci95": f"[{round(m(did)-ci95_halfwidth(did),3)}, {round(m(did)+ci95_halfwidth(did),3)}]",
    }

    required = power.get("required_n", [])
    did_power = power.get("did_summary", {})

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V10 expanded statistics report</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; color: #172033; background: #f5f7fa; }}
    header {{ background: #17375e; color: white; padding: 50px 6vw; }}
    h1 {{ font-size: 48px; margin: 0 0 12px; letter-spacing: 0; }}
    h2 {{ font-size: 30px; margin: 0 0 14px; }}
    h3 {{ font-size: 22px; margin: 22px 0 8px; }}
    p, li {{ font-size: 18px; line-height: 1.75; }}
    section {{ max-width: 1160px; margin: 0 auto; padding: 38px 6vw; background: white; border-bottom: 1px solid #dfe6ef; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0 28px; font-size: 15px; }}
    th, td {{ border: 1px solid #dfe6ef; padding: 9px 10px; text-align: left; }}
    th {{ background: #eef3f8; }}
    figure {{ margin: 28px 0 42px; }}
    img {{ width: 100%; border: 1px solid #dfe6ef; border-radius: 8px; background: white; }}
    figcaption {{ margin-top: 10px; font-size: 17px; line-height: 1.7; color: #435066; }}
    code {{ background: #edf1f5; padding: 2px 6px; border-radius: 5px; }}
    .metric {{ font-size: 32px; font-weight: 760; color: #17375e; margin: 8px 0; }}
    .note {{ color: #5e6b78; }}
  </style>
</head>
<body>
  <header>
    <p>V10 expanded · 30 matched LLM sessions per condition · session-level statistics</p>
    <h1>V10 统计版报告</h1>
    <p>本报告用 LLM session 作为统计单位，并在图中显示跨 session 的 95% CI。单个 session 内的 12 个 choice rounds 被视为重复测量，不当作独立被试。</p>
  </header>

  <section>
    <h2>主要结论</h2>
    <p>扩展版支持一个小但可靠的 <strong>orthogonality-release effect</strong>：明确说明“陈述真假与返还行为无关”后，低诚实对象的投资惩罚被削弱，但没有出现 V9 那种强反转。</p>
    <div class="metric">DID = {did_summary['mean_DID']}</div>
    <p>session-level normal/t 近似 p = <strong>{did_summary['normal_p']}</strong>；随机符号翻转检验 p = <strong>{did_summary['signflip_p']}</strong>；95% CI = <strong>{did_summary['ci95']}</strong>。</p>
    {html_table([did_summary])}
  </section>

  <section>
    <h2>统计单位与误差条</h2>
    <p>误差条不是 1440 个 choice rounds 的 SEM，而是跨 LLM sessions 的 95% CI。这样更接近心理学实验里的被试层面统计：一个 LLM session 相当于一个完整 repeated-game episode，session 内的 choice rounds 是 repeated measures。</p>
    <ul>
      <li><strong>LLM session：</strong>一个完整 episode，包含标准化观察、12 轮投资和 final probe。</li>
      <li><strong>matched scenario id：</strong>刺激材料编号，用来让 high/low honesty 看到可比较的返还序列。</li>
      <li><strong>choice round：</strong>session 内的一轮投资决策，不作为独立被试。</li>
    </ul>
  </section>

  <section>
    <h2>误差条图</h2>
    <figure>
      <img src="figures/stats_investment_trajectory_ci.png" alt="Investment trajectory with CI">
      <figcaption>图 1. 每一轮投资的平均值和 95% CI。虚线表示中途信息出现的位置。</figcaption>
    </figure>
    <figure>
      <img src="figures/stats_phase_means_ci.png" alt="Phase means with CI">
      <figcaption>图 2. pre/post 阶段的 session-level 平均投资。低诚实对象始终低于高诚实对象，但 orthogonality 条件下 post 阶段差距较小。</figcaption>
    </figure>
    <figure>
      <img src="figures/stats_honesty_gap_ci.png" alt="Honesty gap with CI">
      <figcaption>图 3. matched-session 的 low-high gap。neutral 条件下 gap 变得更负，orthogonality 条件下 gap 基本不再恶化。</figcaption>
    </figure>
    <figure>
      <img src="figures/stats_final_probe_ci.png" alt="Final probe with CI">
      <figcaption>图 4. final probe 的 95% CI。probe 是辅助解释；主要行为结论来自 investment data。</figcaption>
    </figure>
  </section>

  <section>
    <h2>Phase-level 统计</h2>
    {html_table(phase_table)}
    <h3>Low-high gap</h3>
    {html_table(gap_table)}
  </section>

  <section>
    <h2>Power analysis 怎么算</h2>
    <p>power analysis 使用当前 30 个 matched sessions 的 DID 作为效应估计。先计算每个 matched scenario 的 DID，再得到均值和标准差：</p>
    <pre>DID_i =
[(low - high)_post - (low - high)_pre]_orthogonality
- [(low - high)_post - (low - high)_pre]_neutral</pre>
    <p>当前估计：mean = <strong>{did_power.get('mean')}</strong>，SD = <strong>{did_power.get('sd')}</strong>，dz = <strong>{did_power.get('cohens_dz')}</strong>。所需样本量用近似公式：</p>
    <pre>n = ((z_(1-alpha/2) + z_power) / dz)^2</pre>
    <p>这里 alpha = .05 双侧检验。80% power 使用 z_power = 0.842；90% power 使用 z_power = 1.282；95% power 使用 z_power = 1.645。</p>
    {html_table(required)}
    <p>80% power 的意思是：如果真实效应等于当前观察到的效应，重复做很多次同样实验，大约 80% 能检出 p&lt;.05。90% power 更保守，需要更多 sessions，假阴性风险更低。</p>
    <p class="note">注意：这是基于当前 pilot/expanded 数据的效应大小估计。如果真实效应比当前小，所需 session 会更多；如果真实效应更大，所需 session 会更少。</p>
  </section>
</body>
</html>
"""
    (SESSION / "report.html").write_text(report, encoding="utf-8")
    (SESSION / "stats_summary.json").write_text(
        json.dumps(
            {
                "did_summary": did_summary,
                "phase_table": phase_table,
                "gap_table": gap_table,
                "power_required_n": required,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {SESSION / 'report.html'}")
    print(f"Wrote {SESSION / 'stats_summary.json'}")


if __name__ == "__main__":
    main()
