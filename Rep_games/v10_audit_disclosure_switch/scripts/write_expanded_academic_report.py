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
TCRIT_CACHE: dict[int, float] = {}


def read_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in ["run_id", "seed_index", "choice_trial"]:
                if row.get(key) not in {"", None}:
                    row[key] = int(float(row[key]))
            for key in ["investment", "payoff", "return_rate"]:
                if row.get(key) not in {"", None}:
                    row[key] = float(row[key])
            rows.append(row)
    return rows


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def avg(values: list[float]) -> float:
    return mean(values) if values else float("nan")


def sd(values: list[float]) -> float:
    return stdev(values) if len(values) > 1 else float("nan")


def se(values: list[float]) -> float:
    return sd(values) / math.sqrt(len(values)) if len(values) > 1 else float("nan")


def t_pdf(x: float, df: int) -> float:
    numerator = math.gamma((df + 1) / 2)
    denominator = math.sqrt(df * math.pi) * math.gamma(df / 2)
    return numerator / denominator * (1 + (x * x) / df) ** (-(df + 1) / 2)


def t_cdf(x: float, df: int, steps: int = 20000) -> float:
    if x == 0:
        return 0.5
    sign = 1 if x > 0 else -1
    upper = abs(x)
    if steps % 2:
        steps += 1
    h = upper / steps
    total = t_pdf(0, df) + t_pdf(upper, df)
    for i in range(1, steps):
        total += (4 if i % 2 else 2) * t_pdf(i * h, df)
    area = total * h / 3
    return 0.5 + sign * area


def t_p_two_sided(t_value: float, df: int) -> float:
    return 2 * (1 - t_cdf(abs(t_value), df))


def t_critical_975(df: int) -> float:
    if df in TCRIT_CACHE:
        return TCRIT_CACHE[df]
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < 0.975:
            lo = mid
        else:
            hi = mid
    TCRIT_CACHE[df] = (lo + hi) / 2
    return TCRIT_CACHE[df]


def ci95(values: list[float]) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    half = t_critical_975(len(values) - 1) * se(values) if len(values) > 1 else 0
    return avg(values) - half, avg(values) + half


def sem_interval(values: list[float]) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    half = se(values) if len(values) > 1 else 0
    return avg(values) - half, avg(values) + half


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return ""
    return f"{number:.{digits}f}"


def html_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]] | None = None) -> str:
    if not rows:
        return "<p class='muted'>暂无结果。</p>"
    if columns is None:
        columns = [(key, key) for key in rows[0].keys()]
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = []
        for key, _label in columns:
            value = row.get(key, "")
            cells.append(f"<td>{html.escape(str(value))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def phase_session_values(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[float]]:
    buckets: dict[tuple[str, str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        buckets[(row["midpoint_message"], row["honesty_level"], row["phase"], int(row["run_id"]))].append(
            float(row["investment"])
        )
    out: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for (midpoint, honesty, phase, _run), values in buckets.items():
        out[(midpoint, honesty, phase)].append(avg(values))
    return out


def per_round_values(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], list[float]]:
    out: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        out[(row["midpoint_message"], row["honesty_level"], int(row["choice_trial"]))].append(
            float(row["investment"])
        )
    return out


def matched_gap_values(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[float]]:
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
                    out[(midpoint, phase)].append(avg(low) - avg(high))
    return out


def did_values(rows: list[dict[str, Any]]) -> list[float]:
    gaps = matched_gap_values(rows)
    n = min(
        len(gaps[("neutral_reminder", "pre")]),
        len(gaps[("neutral_reminder", "post")]),
        len(gaps[("orthogonality_disclosure", "pre")]),
        len(gaps[("orthogonality_disclosure", "post")]),
    )
    values = []
    for idx in range(n):
        neutral_change = gaps[("neutral_reminder", "post")][idx] - gaps[("neutral_reminder", "pre")][idx]
        orth_change = (
            gaps[("orthogonality_disclosure", "post")][idx]
            - gaps[("orthogonality_disclosure", "pre")][idx]
        )
        values.append(orth_change - neutral_change)
    return values


def signflip_p(values: list[float], sims: int = 200000) -> float:
    observed = abs(avg(values))
    if len(values) <= 18:
        total = 0
        hit = 0
        for signs in itertools.product([-1, 1], repeat=len(values)):
            total += 1
            stat = abs(avg([value * sign for value, sign in zip(values, signs)]))
            if stat >= observed - 1e-12:
                hit += 1
        return hit / total
    rng = random.Random(20260529)
    hit = 0
    for _ in range(sims):
        stat = abs(avg([value * (1 if rng.random() < 0.5 else -1) for value in values]))
        if stat >= observed - 1e-12:
            hit += 1
    return hit / sims


def one_sample_t(values: list[float]) -> dict[str, Any]:
    n = len(values)
    t_value = avg(values) / se(values)
    p_value = t_p_two_sided(t_value, n - 1)
    lo, hi = ci95(values)
    return {
        "n": n,
        "mean": avg(values),
        "sd": sd(values),
        "se": se(values),
        "t": t_value,
        "df": n - 1,
        "p": p_value,
        "signflip_p": signflip_p(values),
        "ci_low": lo,
        "ci_high": hi,
        "dz": avg(values) / sd(values),
    }


def phase_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = phase_session_values(rows)
    out = []
    labels = {
        "neutral_reminder": "Neutral reminder",
        "orthogonality_disclosure": "Orthogonality disclosure",
        "high": "High honesty",
        "low": "Low honesty",
        "pre": "Pre",
        "post": "Post",
    }
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for honesty in ["high", "low"]:
            for phase in ["pre", "post"]:
                vals = values[(midpoint, honesty, phase)]
                lo, hi = sem_interval(vals)
                out.append(
                    {
                        "condition": labels[midpoint],
                        "honesty": labels[honesty],
                        "phase": labels[phase],
                        "n sessions": len(vals),
                        "mean investment": fmt(avg(vals)),
                        "SEM": fmt(se(vals)),
                        "mean ± SEM": f"{fmt(avg(vals))} ± {fmt(se(vals))}",
                    }
                )
    return out


def gap_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = matched_gap_values(rows)
    labels = {
        "neutral_reminder": "Neutral reminder",
        "orthogonality_disclosure": "Orthogonality disclosure",
        "pre": "Pre",
        "post": "Post",
    }
    out = []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        pre = gaps[(midpoint, "pre")]
        post = gaps[(midpoint, "post")]
        change = [b - a for a, b in zip(pre, post)]
        out.append(
            {
                "condition": labels[midpoint],
                "pre low-high": fmt(avg(pre)),
                "post low-high": fmt(avg(post)),
                "post-pre change": fmt(avg(change)),
                "SEM for change": fmt(se(change)),
                "change ± SEM": f"{fmt(avg(change))} ± {fmt(se(change))}",
            }
        )
    return out


def probe_table(probe_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {
        "neutral_reminder": "Neutral reminder",
        "orthogonality_disclosure": "Orthogonality disclosure",
        "high": "High honesty",
        "low": "Low honesty",
    }
    metrics = [
        ("moral_trust", "Moral trust"),
        ("expected_return_rate", "Expected return rate"),
        ("truth_return_link", "Perceived truth-return link"),
        ("controllability", "Perceived controllability"),
    ]
    out = []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for honesty in ["high", "low"]:
            row = {"condition": labels[midpoint], "honesty": labels[honesty]}
            subset = [
                item
                for item in probe_rows
                if item["midpoint_message"] == midpoint and item["honesty_level"] == honesty
            ]
            row["n complete probes"] = len(subset)
            for key, label in metrics:
                vals = [float(item[key]) for item in subset if item.get(key) not in {"", None}]
                row[label] = fmt(avg(vals)) if vals else ""
            out.append(row)
    return out


def make_plots(rows: list[dict[str, Any]], probe_rows: list[dict[str, Any]]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    colors = {"high": "#2f6f9f", "low": "#d95f59"}
    labels = {
        "neutral_reminder": "Neutral reminder",
        "orthogonality_disclosure": "Orthogonality disclosure",
        "high": "High honesty",
        "low": "Low honesty",
    }

    round_values = per_round_values(rows)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharey=True)
    for ax, midpoint in zip(axes, ["neutral_reminder", "orthogonality_disclosure"]):
        for honesty in ["high", "low"]:
            xs, ys, errs = [], [], []
            for trial in range(1, 13):
                vals = round_values[(midpoint, honesty, trial)]
                lo, hi = sem_interval(vals)
                xs.append(trial)
                ys.append(avg(vals))
                errs.append((hi - lo) / 2)
            ax.errorbar(
                xs,
                ys,
                yerr=errs,
                marker="o",
                capsize=3,
                linewidth=2.4,
                color=colors[honesty],
                label=labels[honesty],
            )
        ax.axvline(6.5, color="#4b5563", linestyle="--", linewidth=1.3)
        ax.set_title(labels[midpoint], fontsize=14)
        ax.set_xlabel("Choice round", fontsize=12)
        ax.set_ylim(0, 10)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Mean investment (± SEM)", fontsize=12)
    axes[1].legend(frameon=False)
    fig.suptitle("Investment across choice rounds", fontsize=16)
    fig.tight_layout()
    fig.savefig(FIG / "academic_investment_rounds.png", dpi=200)
    plt.close(fig)

    phase_values = phase_session_values(rows)
    x_labels, means, errs, bar_colors = [], [], [], []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            for honesty in ["high", "low"]:
                vals = phase_values[(midpoint, honesty, phase)]
                lo, hi = sem_interval(vals)
                x_labels.append(f"{labels[midpoint]}\n{phase.capitalize()}\n{labels[honesty]}")
                means.append(avg(vals))
                errs.append((hi - lo) / 2)
                bar_colors.append(colors[honesty])
    fig, ax = plt.subplots(figsize=(14, 5.8))
    ax.bar(np.arange(len(x_labels)), means, yerr=errs, capsize=4, color=bar_colors)
    ax.set_xticks(np.arange(len(x_labels)), x_labels, rotation=20, ha="right")
    ax.set_ylabel("Session mean investment (± SEM)", fontsize=12)
    ax.set_title("Mean investment before and after the midpoint message", fontsize=16)
    ax.set_ylim(0, 7)
    fig.tight_layout()
    fig.savefig(FIG / "academic_phase_means.png", dpi=200)
    plt.close(fig)

    gaps = matched_gap_values(rows)
    x_labels, means, errs, bar_colors = [], [], [], []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            vals = gaps[(midpoint, phase)]
            lo, hi = sem_interval(vals)
            x_labels.append(f"{labels[midpoint]}\n{phase.capitalize()}")
            means.append(avg(vals))
            errs.append((hi - lo) / 2)
            bar_colors.append("#7a8f3a" if midpoint == "neutral_reminder" else "#9b5de5")
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.bar(x_labels, means, yerr=errs, capsize=4, color=bar_colors)
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_ylabel("Low honesty - high honesty investment (± SEM)", fontsize=12)
    ax.set_title("Honesty penalty by phase", fontsize=16)
    fig.tight_layout()
    fig.savefig(FIG / "academic_honesty_gap.png", dpi=200)
    plt.close(fig)

    if probe_rows:
        metrics = [
            ("moral_trust", "Moral trust", (0, 100)),
            ("expected_return_rate", "Expected return rate", (0, 1)),
            ("truth_return_link", "Perceived truth-return link", (0, 100)),
            ("controllability", "Perceived controllability", (0, 100)),
        ]
        fig, axes = plt.subplots(2, 2, figsize=(13, 8.2))
        for ax, (metric, title, ylim) in zip(axes.flatten(), metrics):
            x_labels, means, errs, bar_colors = [], [], [], []
            for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
                for honesty in ["high", "low"]:
                    vals = [
                        float(row[metric])
                        for row in probe_rows
                        if row["midpoint_message"] == midpoint
                        and row["honesty_level"] == honesty
                        and row.get(metric) not in {"", None}
                    ]
                    lo, hi = sem_interval(vals)
                    x_labels.append(f"{labels[midpoint]}\n{labels[honesty]}")
                    means.append(avg(vals))
                    errs.append((hi - lo) / 2 if vals else 0)
                    bar_colors.append(colors[honesty])
            ax.bar(np.arange(len(x_labels)), means, yerr=errs, capsize=4, color=bar_colors)
            ax.set_xticks(np.arange(len(x_labels)), x_labels, rotation=18, ha="right", fontsize=8)
            ax.set_ylim(*ylim)
            ax.set_title(title)
        fig.suptitle("Post-task probe ratings", fontsize=16)
        fig.tight_layout()
        fig.savefig(FIG / "academic_final_probe.png", dpi=200)
        plt.close(fig)


def main() -> None:
    rows = read_csv(SESSION / "trial_level_data.csv")
    probe_rows = read_csv(SESSION / "final_probe_data.csv") if (SESSION / "final_probe_data.csv").exists() else []
    power = read_json(SESSION / "power_analysis.json", {})
    make_plots(rows, probe_rows)

    did = did_values(rows)
    did_stats = one_sample_t(did)
    gaps = matched_gap_values(rows)
    neutral_pre = avg(gaps[("neutral_reminder", "pre")])
    neutral_post = avg(gaps[("neutral_reminder", "post")])
    orth_pre = avg(gaps[("orthogonality_disclosure", "pre")])
    orth_post = avg(gaps[("orthogonality_disclosure", "post")])

    required = power.get("required_n", [])
    power_curve = power.get("power_curve", [])

    stats_payload = {
        "did": {key: (round(value, 6) if isinstance(value, float) else value) for key, value in did_stats.items()},
        "neutral_pre_low_minus_high": round(neutral_pre, 6),
        "neutral_post_low_minus_high": round(neutral_post, 6),
        "orthogonality_pre_low_minus_high": round(orth_pre, 6),
        "orthogonality_post_low_minus_high": round(orth_post, 6),
        "phase_table": phase_table(rows),
        "gap_table": gap_table(rows),
        "probe_table": probe_table(probe_rows),
        "required_n": required,
        "power_curve": power_curve,
    }
    (SESSION / "academic_stats_summary.json").write_text(
        json.dumps(stats_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V10 扩展实验报告</title>
  <style>
    :root {{
      --ink: #162033;
      --muted: #5f6e7f;
      --line: #dde5ee;
      --soft: #f5f7fa;
      --blue: #17375e;
      --red: #b64a4a;
    }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; color: var(--ink); background: var(--soft); }}
    header {{ background: #17375e; color: white; padding: 56px 6vw 62px; }}
    header p {{ max-width: 980px; font-size: 21px; line-height: 1.7; }}
    h1 {{ font-size: clamp(42px, 5vw, 68px); margin: 0 0 16px; letter-spacing: 0; }}
    h2 {{ font-size: 31px; margin: 0 0 16px; }}
    h3 {{ font-size: 22px; margin: 25px 0 10px; }}
    p, li {{ font-size: 18px; line-height: 1.78; }}
    section {{ max-width: 1160px; margin: 0 auto; padding: 40px 6vw; background: white; border-bottom: 1px solid var(--line); }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0 30px; font-size: 15px; }}
    th, td {{ border: 1px solid var(--line); padding: 10px 11px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    figure {{ margin: 28px 0 44px; }}
    img {{ width: 100%; border: 1px solid var(--line); border-radius: 8px; background: white; }}
    figcaption {{ margin-top: 10px; font-size: 17px; line-height: 1.68; color: #435066; }}
    code {{ background: #edf1f5; padding: 2px 6px; border-radius: 5px; }}
    pre {{ background: #111827; color: #eef6ff; padding: 16px 18px; border-radius: 8px; overflow-x: auto; line-height: 1.6; }}
    .abstract {{ font-size: 20px; color: #253448; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
    .card {{ border: 1px solid var(--line); border-radius: 8px; padding: 18px; background: #fff; }}
    .metric {{ font-size: 30px; font-weight: 760; color: var(--blue); margin: 4px 0 8px; }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 820px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <p>V10 expanded · MiniMax-M2.7 · 30 matched LLM sessions per condition</p>
    <h1>显性规则能否削弱低诚实带来的投资惩罚？</h1>
    <p>本实验检验大语言模型在重复信任博弈中，是否能在行为上区分“事实诚实性”和“工具性收益”。</p>
  </header>

  <section>
    <h2>摘要</h2>
    <p class="abstract">前序实验显示，模型会把 partner 的事实诚实性带入投资决策：即使返还证据相同，低诚实对象也会获得更低投资。V10 进一步检验这种惩罚是否可以被显性规则纠正。每个 LLM session 先观察同一 partner 的标准化返还记录，随后完成 12 轮逐轮投资；中途随机插入普通提醒或正交性说明，即“陈述真假与返还行为独立”。扩展实验包含 30 个 matched sessions。结果显示，正交性说明并未使低诚实对象获得高于高诚实对象的投资，但显著减弱了低诚实惩罚，DID = {fmt(did_stats['mean'])}, SEM = {fmt(did_stats['se'])}, t({did_stats['df']}) = {fmt(did_stats['t'])}, p = {fmt(did_stats['p'], 4)}；随机符号翻转检验 p = {fmt(did_stats['signflip_p'], 4)}。这说明模型能部分利用显性规则调整社会性惩罚，但这种调整是不完全的。</p>
  </section>

  <section>
    <h2>研究问题</h2>
    <p>V8 发现，在返还率匹配的情况下，低诚实 partner 仍然获得更少投资。V9 进一步发现，当提示词明确说明“诚实性与返还无关”时，低诚实对象在某些条件下反而获得很高投资。V10 因此不再简单重复 honesty bias，而是检验一个更具体的问题：</p>
    <p><strong>当模型已经观察到相同的返还证据后，显性正交说明是否会削弱低诚实带来的投资惩罚？</strong></p>
    <p>这个问题重要，是因为它把三件事分开：模型对收益的学习、模型对诚实性的社会评价，以及显性规则能否改变后续行为。如果模型显性知道诚实性与返还无关，但仍然降低投资，那么说明行为决策中保留了独立于收益预期的社会性折扣。</p>
  </section>

  <section>
    <h2>实验设计</h2>
    <div class="grid">
      <div class="card">
        <h3>Manipulation 1</h3>
        <div class="metric">Honesty</div>
        <p>High honesty partner 的陈述大多数为真；low honesty partner 的陈述大多数为假。</p>
      </div>
      <div class="card">
        <h3>Manipulation 2</h3>
        <div class="metric">Midpoint message</div>
        <p>第 6 轮投资后，模型收到普通提醒或正交性说明。</p>
      </div>
      <div class="card">
        <h3>Within-session factor</h3>
        <div class="metric">Phase</div>
        <p>每个 session 分为 pre 和 post 两段，每段 6 轮投资。</p>
      </div>
    </div>
    <p>每个 session 开始前有 8 条标准化观察记录。系统固定向 Alex 投资 5 tokens，因此模型能在正式决策前看到可比较的返还证据。正式投资阶段，模型每轮有 10 tokens，可投资 0 到 10；投资会被三倍给 Alex，Alex 再返还一定 tokens。本轮收益定义为：</p>
    <pre>payoff = 10 - investment + returned tokens</pre>
    <p>扩展实验共 120 个完整 LLM sessions：2 个 honesty 条件 × 2 个 midpoint message 条件 × 30 个 matched scenario ids。每个 session 内有 12 个 choice rounds，因此共有 1440 个投资决策。统计检验以 session 为独立单位，choice rounds 被视为 session 内重复测量。</p>
  </section>

  <section>
    <h2>主要分析</h2>
    <p>核心因变量是每轮投资额。主要检验不是简单比较 high 与 low honesty，而是比较低诚实惩罚在中途说明前后如何变化。对每个 matched scenario 计算：</p>
    <pre>DID_i =
[(low - high)_post - (low - high)_pre]_orthogonality
- [(low - high)_post - (low - high)_pre]_neutral</pre>
    <h3>DID 是什么</h3>
    <p>DID 是 difference-in-differences，即“差异中的差异”。这里我们关心的不是模型总体投得多不多，而是低诚实对象相对于高诚实对象受到了多大惩罚。因此第一步先计算 <strong>low-high gap</strong>：</p>
    <pre>low-high gap = mean investment_low honesty - mean investment_high honesty</pre>
    <p>这个值通常是负数。负数越大，表示低诚实对象相对高诚实对象拿到的投资越少，也就是低诚实惩罚越强。</p>
    <p>第二步看这个惩罚从 pre 到 post 是否改变：</p>
    <pre>gap change = gap_post - gap_pre</pre>
    <p>如果 gap change 为正，说明 low-high gap 变得不那么负，低诚实惩罚被削弱；如果为负，说明低诚实惩罚进一步增强。</p>
    <p>第三步再用 orthogonality disclosure 的 gap change 减去 neutral reminder 的 gap change。这样做是为了扣除重复互动中自然发生的时间变化、学习变化、以及“中途多出现一条信息”本身的影响。换句话说，neutral reminder 是基线漂移，orthogonality disclosure 是基线漂移加上正交性说明的作用；两者相减后，才更接近正交性说明本身对低诚实惩罚的影响。</p>
    <pre>DID = gap change_orthogonality - gap change_neutral</pre>
    <p>如果 DID 大于 0，说明正交性说明相对于普通提醒，释放了低诚实对象受到的投资惩罚。我们对 30 个 matched-scenario DID 值进行单样本 t 检验，并报告随机符号翻转检验作为稳健性检验。</p>
  </section>

  <section>
    <h2>结果</h2>
    <h3>核心结果</h3>
    <p>普通提醒条件下，low-high gap 从 pre 阶段的 {fmt(neutral_pre)} 变为 post 阶段的 {fmt(neutral_post)}，低诚实惩罚进一步增大。正交性说明条件下，low-high gap 从 {fmt(orth_pre)} 变为 {fmt(orth_post)}，低诚实惩罚基本不再恶化。两者合成的 DID 为 {fmt(did_stats['mean'])}。</p>
    <p>具体地说，普通提醒条件下的 gap change 是 {fmt(neutral_post - neutral_pre)}，说明低诚实惩罚随互动推进而增强；正交性说明条件下的 gap change 是 {fmt(orth_post - orth_pre)}，说明低诚实惩罚几乎没有继续增强。因此 DID = {fmt(orth_post - orth_pre)} - ({fmt(neutral_post - neutral_pre)}) = {fmt(did_stats['mean'])}。</p>
    <div class="grid">
      <div class="card">
        <h3>DID</h3>
        <div class="metric">{fmt(did_stats['mean'])}</div>
        <p class="muted">正值表示正交性说明削弱低诚实惩罚。</p>
      </div>
      <div class="card">
        <h3>SEM</h3>
        <div class="metric">{fmt(did_stats['se'])}</div>
        <p class="muted">以 matched sessions 为单位。</p>
      </div>
      <div class="card">
        <h3>t-test / sign-flip</h3>
        <div class="metric">p = {fmt(did_stats['p'], 4)}</div>
        <p class="muted">单样本 t 检验；符号翻转 p = {fmt(did_stats['signflip_p'], 4)}。</p>
      </div>
    </div>
    <h3>阶段均值</h3>
    {html_table(phase_table(rows))}
    <h3>低诚实惩罚的变化</h3>
    {html_table(gap_table(rows))}
  </section>

  <section>
    <h2>图示</h2>
    <figure>
      <img src="figures/academic_investment_rounds.png" alt="Investment by round">
      <figcaption>图 1. 12 轮投资中的平均投资额。虚线表示中途信息出现的位置。误差条表示跨 LLM sessions 的 ±1 SEM。</figcaption>
    </figure>
    <figure>
      <img src="figures/academic_phase_means.png" alt="Phase means">
      <figcaption>图 2. pre/post 阶段的 session-level 平均投资。低诚实对象整体投资较低，但正交性说明后差距不再继续扩大。</figcaption>
    </figure>
    <figure>
      <img src="figures/academic_honesty_gap.png" alt="Honesty gap">
      <figcaption>图 3. 每个条件下的 low-high gap。普通提醒条件下低诚实惩罚增强；正交性说明条件下低诚实惩罚保持稳定，形成正向 DID。</figcaption>
    </figure>
    <figure>
      <img src="figures/academic_final_probe.png" alt="Final probe">
      <figcaption>图 4. 任务结束后的显性判断。Final probe 只作为辅助解释，不进入逐轮决策过程。</figcaption>
    </figure>
  </section>

  <section>
    <h2>Final probe</h2>
    <p>投资结束后，模型报告 moral trust、expected return rate、truth-return link 和 controllability。Probe 的作用是检查模型显性上如何理解 partner，而不是主要行为因变量。扩展实验中 114/120 个 session 返回完整 probe JSON。</p>
    {html_table(probe_table(probe_rows))}
    <p>整体模式与行为结果一致：模型能在 expected return 层面部分分离返还预期与诚实性，但 moral trust 仍然强烈区分高诚实与低诚实对象。</p>
  </section>

  <section>
    <h2>Power analysis</h2>
    <p>Power analysis 基于当前 30 个 matched sessions 的 DID 效应大小估计。当前 dz = {fmt(did_stats['dz'])}。使用双侧 alpha = .05 的近似公式：</p>
    <pre>n = ((z_(1-alpha/2) + z_power) / dz)^2</pre>
    {html_table(required)}
    <p>80% power 表示如果真实效应等于当前估计，重复同样实验时约 80% 能检出 p &lt; .05；90% power 更保守，假阴性风险更低，因此需要更多 sessions。按当前效应估计，50 个 matched sessions 可达到约 80% power，67 个 matched sessions 可达到约 90% power。</p>
    {html_table(power_curve)}
  </section>

  <section>
    <h2>解释与限制</h2>
    <p>V10 扩展实验不支持“低诚实对象在正交说明后获得更高投资”的强反转版本。更稳妥的结论是：显性正交说明能削弱低诚实惩罚，但不能完全消除它。这个结果将 V9 的强反转收缩成一个更可信的机制：模型可以使用任务规则修正 honesty-to-payoff 的错误泛化，但社会性评价仍然会残留在投资行为中。</p>
    <p>本实验仍是单模型结果，且对象、任务和提示结构都比较简化。下一步应在更多模型上复现，并在更接近人类实验的界面中比较 LLM 与真实被试：人类是否也会在显性知道“诚实性与收益无关”后保留类似的信任折扣？如果会，那么该范式可以作为研究社会信任与工具性收益分离的共同任务；如果不会，则说明 LLM 的社会决策存在特有的规则-行为分离。</p>
  </section>

  <section>
    <h2>一句话结论</h2>
    <p><strong>V10 表明，大语言模型能被显性规则部分纠正，但低诚实带来的社会性折扣不会完全消失。</strong></p>
  </section>
</body>
</html>
"""
    (SESSION / "report.html").write_text(report, encoding="utf-8")
    print(f"Wrote {SESSION / 'report.html'}")
    print(f"Wrote {SESSION / 'academic_stats_summary.json'}")


if __name__ == "__main__":
    main()
