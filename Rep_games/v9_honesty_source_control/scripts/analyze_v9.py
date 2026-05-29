from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"
DESIGN_PATH = ROOT / "conditions" / "design.json"
RESULTS_PATH = OUT / "results.json"
RUN_CONDITIONS_PATH = OUT / "run_conditions.json"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_trials(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for run in results:
        for trial in run.get("trial_results", []):
            rows.append(
                {
                    "run_id": run["run_id"],
                    "model": run.get("model"),
                    "block": run["block"],
                    "statement_mode": run["statement_mode"],
                    "honesty_level": run["honesty_level"],
                    "return_policy": run["return_policy"],
                    "presentation_mode": run["presentation_mode"],
                    "orthogonality_instruction": run["orthogonality_instruction"],
                    "seed_index": run["seed_index"],
                    "trial": trial["trial"],
                    "statement_true": trial["statement_true"],
                    "return_rate": trial["return_rate"],
                    "investment": trial["investment"],
                    "returned_tokens": trial["returned_tokens"],
                    "payoff": trial["payoff"],
                    "net_gain_from_investment": trial["net_gain_from_investment"],
                    "cumulative_truth_rate_before": trial.get("cumulative_truth_rate_before"),
                    "cumulative_return_rate_before": trial.get("cumulative_return_rate_before"),
                    "previous_payoff": trial.get("previous_payoff"),
                }
            )
    return rows


def write_trial_csv(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path = OUT / "trial_level_data.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def group_means(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row[key] for key in keys)].append(row)
    out = []
    for key_values, items in sorted(buckets.items()):
        out.append(
            {
                **dict(zip(keys, key_values)),
                "n_trials": len(items),
                "n_runs": len({item["run_id"] for item in items}),
                "mean_investment": round(mean(item["investment"] for item in items), 3),
                "mean_return_rate": round(mean(item["return_rate"] for item in items), 3),
                "mean_payoff": round(mean(item["payoff"] for item in items), 3),
            }
        )
    return out


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(x) != len(y):
        return None
    mx = mean(x)
    my = mean(y)
    sx = sum((item - mx) ** 2 for item in x)
    sy = sum((item - my) ** 2 for item in y)
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sx * sy)


def diagnostic_correlations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = [
        ("investment_vs_cumulative_truth", "investment", "cumulative_truth_rate_before"),
        ("investment_vs_cumulative_return", "investment", "cumulative_return_rate_before"),
        ("investment_vs_previous_payoff", "investment", "previous_payoff"),
    ]
    out = {}
    for label, y_key, x_key in pairs:
        x = []
        y = []
        for row in rows:
            xv = safe_float(row.get(x_key))
            yv = safe_float(row.get(y_key))
            if xv is not None and yv is not None:
                x.append(xv)
                y.append(yv)
        r = pearson(x, y)
        out[label] = {"n": len(x), "r": round(r, 3) if r is not None else None}
    return out


def plot_main(rows: list[dict[str, Any]]) -> list[str]:
    FIG.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    if not rows:
        return paths

    main_rows = [
        row
        for row in rows
        if row["block"] == "main_partner_honesty"
        and row["orthogonality_instruction"] == "standard"
    ]
    if main_rows:
        summary = group_means(main_rows, ["return_policy", "honesty_level"])
        labels = [f"{item['return_policy']}\n{item['honesty_level']}" for item in summary]
        values = [item["mean_investment"] for item in summary]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(labels, values, color=["#2f6f9f", "#d95f59", "#2f6f9f", "#d95f59"][: len(values)])
        ax.set_ylabel("Mean investment")
        ax.set_title("Main design: honesty effect within return policy")
        ax.set_ylim(0, 10)
        fig.tight_layout()
        path = FIG / "main_investment_by_honesty_return.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        paths.append(path.relative_to(OUT).as_posix())

    control_rows = [
        row
        for row in rows
        if row["block"] in {"no_statement_control", "irrelevant_truth_control", "cheap_talk_only_control"}
    ]
    if control_rows:
        summary = group_means(control_rows, ["block", "return_policy"])
        labels = [f"{item['block'].replace('_control', '')}\n{item['return_policy']}" for item in summary]
        values = [item["mean_investment"] for item in summary]
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.bar(labels, values, color="#7a8f3a")
        ax.set_ylabel("Mean investment")
        ax.set_title("Control conditions")
        ax.set_ylim(0, 10)
        ax.tick_params(axis="x", labelrotation=20)
        fig.tight_layout()
        path = FIG / "control_investment.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        paths.append(path.relative_to(OUT).as_posix())

    return paths


def html_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "<p class='muted'>暂无可分析结果。</p>"
    head = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def mean_for(rows: list[dict[str, Any]], **filters: Any) -> dict[str, Any] | None:
    filtered = []
    for row in rows:
        if all(row.get(key) == value for key, value in filters.items()):
            filtered.append(row)
    if not filtered:
        return None
    return {
        "n_trials": len(filtered),
        "mean_investment": round(mean(row["investment"] for row in filtered), 3),
        "mean_payoff": round(mean(row["payoff"] for row in filtered), 3),
    }


def fmt_metric(item: dict[str, Any] | None) -> str:
    if item is None:
        return "暂无成功结果"
    return f"investment={item['mean_investment']}, payoff={item['mean_payoff']}, n={item['n_trials']}"


def current_observations(rows: list[dict[str, Any]], results: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    if not rows:
        return "<p class='muted'>当前还没有 API 结果；这里只呈现实验设计。</p>"

    seq = [row for row in rows if row["presentation_mode"] == "sequential_trial"]
    evidence_runs = [
        run for run in results if run.get("presentation_mode") == "evidence_only" and run.get("block") == "main_partner_honesty"
    ]
    evidence_ok = sum(1 for run in evidence_runs if not run.get("error"))
    evidence_total = len(evidence_runs)
    evidence_note = (
        f"main block 的 evidence-only 当前成功 {evidence_ok}/{evidence_total} runs，失败多为 M2.7 输出长篇推理而非 JSON；因此现阶段不解释 evidence-only 的行为结果。"
        if evidence_total
        else "本轮完整信号只跑 sequential trial-by-trial；evidence-only 暂未作为正式结果运行。"
    )

    correlations = summary.get("diagnostic_correlations", {})
    ret_r = correlations.get("investment_vs_cumulative_return", {}).get("r")
    payoff_r = correlations.get("investment_vs_previous_payoff", {}).get("r")
    truth_r = correlations.get("investment_vs_cumulative_truth", {}).get("r")

    main_fair_high = fmt_metric(
        mean_for(
            seq,
            block="main_partner_honesty",
            honesty_level="high",
            return_policy="fair_high",
            orthogonality_instruction="standard",
        )
    )
    main_fair_low = fmt_metric(
        mean_for(
            seq,
            block="main_partner_honesty",
            honesty_level="low",
            return_policy="fair_high",
            orthogonality_instruction="standard",
        )
    )
    main_unfair_high = fmt_metric(
        mean_for(
            seq,
            block="main_partner_honesty",
            honesty_level="high",
            return_policy="unfair_low",
            orthogonality_instruction="standard",
        )
    )
    main_unfair_low = fmt_metric(
        mean_for(
            seq,
            block="main_partner_honesty",
            honesty_level="low",
            return_policy="unfair_low",
            orthogonality_instruction="standard",
        )
    )
    no_fair = fmt_metric(mean_for(seq, block="no_statement_control", return_policy="fair_high"))
    no_unfair = fmt_metric(mean_for(seq, block="no_statement_control", return_policy="unfair_low"))
    irr_high_fair = fmt_metric(
        mean_for(seq, block="irrelevant_truth_control", honesty_level="high", return_policy="fair_high")
    )
    irr_low_fair = fmt_metric(
        mean_for(seq, block="irrelevant_truth_control", honesty_level="low", return_policy="fair_high")
    )
    cheap_fair = fmt_metric(mean_for(seq, block="cheap_talk_only_control", return_policy="fair_high"))
    cheap_unfair = fmt_metric(mean_for(seq, block="cheap_talk_only_control", return_policy="unfair_low"))

    return f"""
    <ul>
      <li><strong>这是完整 sequential 信号，不含 evidence-only。</strong> 当前完成 {summary.get('successful_runs', 0)} 个 successful runs，{summary.get('trial_rows', len(rows))} 个 trial-level decisions；每个 run 有 18 轮。</li>
      <li><strong>Return policy 仍然是最强信号。</strong> no-statement baseline 中，fair/high 为 {html.escape(no_fair)}；unfair/low 为 {html.escape(no_unfair)}。也就是说，即使没有任何可核验陈述，模型也会强烈根据返还反馈调投资。</li>
      <li><strong>Trial-level tracking 支持这个判断。</strong> investment 与 previous payoff 的相关约为 {html.escape(str(payoff_r))}，与 cumulative return 的相关约为 {html.escape(str(ret_r))}，与 cumulative truth 的相关约为 {html.escape(str(truth_r))}。</li>
      <li><strong>Main partner honesty 在 standard 条件下有方向，但不是压倒性主效应。</strong> 在 fair/high + standard 下，高诚实为 {html.escape(main_fair_high)}，低诚实为 {html.escape(main_fair_low)}；在 unfair/low + standard 下，高诚实为 {html.escape(main_unfair_high)}，低诚实为 {html.escape(main_unfair_low)}。</li>
      <li><strong>Explicit orthogonality 不只是“消除 bias”，而是改变了策略。</strong> 它提示模型 card truth 与 return policy 无因果关系后，honesty effect 不再稳定，说明这条 instruction 会重塑模型的信息使用方式，不能简单当作中性控制。</li>
      <li><strong>Irrelevant truth 没有复制 partner honesty 效应。</strong> fair/high 中，高真实为 {html.escape(irr_high_fair)}，低真实为 {html.escape(irr_low_fair)}。这说明模型不只是把任何真假反馈都机械泛化为合作性。</li>
      <li><strong>Cheap talk 可能轻微抬高投资，但压不过返还政策。</strong> cheap-talk-only 中，fair/high 为 {html.escape(cheap_fair)}，unfair/low 为 {html.escape(cheap_unfair)}。</li>
      <li><strong>Evidence-only 边界。</strong> {html.escape(evidence_note)}</li>
    </ul>
"""


def discussion_takeaways(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>当前还没有结果可讨论。</p>"

    seq = [row for row in rows if row["presentation_mode"] == "sequential_trial"]
    explicit_target = [
        row
        for row in seq
        if row["block"] == "main_partner_honesty"
        and row["return_policy"] == "fair_high"
        and row["orthogonality_instruction"] == "explicit_orthogonality"
    ]
    standard_target = [
        row
        for row in seq
        if row["block"] == "main_partner_honesty"
        and row["return_policy"] == "fair_high"
        and row["orthogonality_instruction"] == "standard"
    ]

    def by_honesty(target: list[dict[str, Any]], honesty: str) -> dict[str, Any] | None:
        selected = [row for row in target if row["honesty_level"] == honesty]
        if not selected:
            return None
        return {
            "mean_investment": round(mean(row["investment"] for row in selected), 3),
            "mean_payoff": round(mean(row["payoff"] for row in selected), 3),
            "n_trials": len(selected),
        }

    natural_high = by_honesty(standard_target, "high")
    natural_low = by_honesty(standard_target, "low")
    explicit_high = by_honesty(explicit_target, "high")
    explicit_low = by_honesty(explicit_target, "low")
    natural_gap = (
        round(natural_high["mean_investment"] - natural_low["mean_investment"], 3)
        if natural_high and natural_low
        else None
    )
    explicit_gap = (
        round(explicit_high["mean_investment"] - explicit_low["mean_investment"], 3)
        if explicit_high and explicit_low
        else None
    )

    phase_rows = []
    for phase, lo, hi in [("前 6 轮", 1, 6), ("中间 6 轮", 7, 12), ("后 6 轮", 13, 18)]:
        high_vals = [
            row["investment"]
            for row in explicit_target
            if row["honesty_level"] == "high" and lo <= int(row["trial"]) <= hi
        ]
        low_vals = [
            row["investment"]
            for row in explicit_target
            if row["honesty_level"] == "low" and lo <= int(row["trial"]) <= hi
        ]
        if high_vals and low_vals:
            phase_rows.append(
                {
                    "phase": phase,
                    "high_honesty": round(mean(high_vals), 3),
                    "low_honesty": round(mean(low_vals), 3),
                    "low_minus_high": round(mean(low_vals) - mean(high_vals), 3),
                }
            )

    v9b_path = ROOT.parent / "v9b_instruction_control" / "output" / "summary.json"
    v9b_text = "V9b 结果尚未生成。"
    if v9b_path.exists():
        try:
            v9b = json.loads(v9b_path.read_text(encoding="utf-8"))
            gap_items = v9b.get("high_low_gaps", [])
            gap_map = {item["instruction_type"]: item["high_minus_low"] for item in gap_items}
            if gap_map:
                v9b_text = (
                    f"V9b 中 natural high-low gap = {gap_map.get('natural')}，"
                    f"attention-control gap = {gap_map.get('attention_control')}，"
                    f"explicit orthogonality gap = {gap_map.get('explicit_orthogonality')}。"
                    "Attention-control 和 natural 同方向，而 explicit 反向，说明反转不是 prompt 更长或更正式造成的，"
                    "更可能来自 truth-return 无关这条因果内容。"
                )
        except json.JSONDecodeError:
            pass

    return f"""
    <p>这几轮讨论后，V9 的解释需要比“honesty bias 是否存在”更细。V8 发现了自然语境下的 honesty bias；V9 显示这个 bias 有边界，而且会被显式因果说明重写。</p>
    <ul>
      <li><strong>V8 与 V9 并不矛盾。</strong> 在 V9 的 natural / standard 条件下，fair/high return 中 high honesty 投资为 {html.escape(str(natural_high['mean_investment'] if natural_high else None))}，low honesty 为 {html.escape(str(natural_low['mean_investment'] if natural_low else None))}，high-low gap = {html.escape(str(natural_gap))}，方向仍和 V8 一致。</li>
      <li><strong>真正新奇的是 explicit 反转。</strong> 在 fair/high + explicit orthogonality 中，high honesty 投资为 {html.escape(str(explicit_high['mean_investment'] if explicit_high else None))}，low honesty 为 {html.escape(str(explicit_low['mean_investment'] if explicit_low else None))}，high-low gap = {html.escape(str(explicit_gap))}。</li>
      <li><strong>这不是 realized payoff orthogonal。</strong> 实验匹配的是 return policy / return_rate schedule；但 realized payoff = 10 - investment + returned_tokens，会被模型自己的 investment 改变。因此早期探索会创造后续 payoff evidence。</li>
      <li><strong>一个有意思的机制猜想是 exploration shift。</strong> 当 prompt 明确说 dishonesty 与 return 无关时，低诚实不再是风险信号，反而可能把模型推向“不要做道德判断，去测试收益规则”的探索模式。</li>
      <li><strong>但目前还不能把它直接叫 risk seeking。</strong> high-honesty explicit 里有 no-learning trap：若早期投 0，模型就拿不到 positive payoff evidence；low-honesty explicit 更早探索，随后被 positive payoff feedback 放大。</li>
      <li><strong>V9b instruction-control 支持 instruction-content explanation。</strong> {html.escape(v9b_text)}</li>
    </ul>
    <h3>Explicit fair/high 的时间轨迹</h3>
    {html_table(phase_rows, ["phase", "high_honesty", "low_honesty", "low_minus_high"])}
    <h3>最值得做的 next step</h3>
    <p>下一步不是单纯加大样本，而是做一个 forced-observation / forced-exploration 版本：前 3 轮让 high/low honesty 两组获得同等 payoff evidence，例如固定投资 5，或展示上一位参与者投资 10 后得到的返还。之后只分析第 4 轮以后的自由投资。</p>
    <p>如果这样之后 explicit-low-honesty 优势消失，说明 V9 的反转主要来自 early exploration artifact；如果仍存在，才更支持“explicit causal framing 增强了低诚实对象下的 exploration / risk-seeking attitude”。</p>
    <p>参数模型上，可以用 causal-gated reinforcement learning：模型同时估计返还率 <code>μ_t</code>、诚实信念 <code>h_t</code>、honesty 是否诊断 return 的 causal gate <code>d_t</code>、探索 bonus、风险厌恶和 choice temperature。关键待检验参数是 <code>β_X</code>：在 explicit 条件下，低诚实是否额外提高探索倾向。</p>
"""


def planned_counts(design: dict[str, Any], runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not runs:
        return []
    rows = []
    for block in design["blocks"]:
        block_runs = [run for run in runs if run["block"] == block["block"]]
        rows.append(
            {
                "block": block["block"],
                "purpose": block["purpose"],
                "runs": len(block_runs),
                "trial_decisions": sum(len(run["trials"]) for run in block_runs),
            }
        )
    return rows


def make_report(
    design: dict[str, Any],
    runs: list[dict[str, Any]],
    results: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    figure_paths: list[str],
) -> None:
    planned = planned_counts(design, runs)
    result_status = (
        f"已完成 {summary.get('successful_runs', 0)} / {len(runs)} runs，"
        f"{len(rows)} 个 trial-level decisions。"
        if results
        else "当前是设计版报告：已生成条件表，但尚未运行 API 结果。"
    )

    main_summary = group_means(
        [row for row in rows if row["block"] == "main_partner_honesty"],
        ["return_policy", "honesty_level", "presentation_mode", "orthogonality_instruction"],
    )
    control_summary = group_means(
        [row for row in rows if row["block"] != "main_partner_honesty"],
        ["block", "return_policy", "honesty_level", "presentation_mode"],
    )

    figs_html = "".join(
        f"<figure><img src='{html.escape(path)}'><figcaption>{html.escape(path)}</figcaption></figure>"
        for path in figure_paths
    )
    if not figs_html:
        figs_html = "<p class='muted'>跑完 API 后，分析脚本会在这里插入主结果图和 control 图。</p>"

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V9 正式主实验设计</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #142033; background: #f6f7f9; }}
    header {{ background: linear-gradient(135deg, #112238, #245f87); color: white; padding: 56px 6vw 64px; }}
    h1 {{ font-size: clamp(34px, 6vw, 68px); line-height: 1.05; margin: 0 0 20px; letter-spacing: 0; }}
    h2 {{ font-size: 30px; margin: 0 0 18px; }}
    h3 {{ font-size: 22px; margin: 24px 0 10px; }}
    p, li {{ font-size: 18px; line-height: 1.75; }}
    code {{ background: #edf1f5; padding: 2px 6px; border-radius: 5px; }}
    section {{ max-width: 1120px; margin: 0 auto; padding: 44px 6vw; background: white; }}
    section + section {{ border-top: 1px solid #e6ebf0; }}
    .lead {{ max-width: 980px; font-size: 24px; color: #eaf2f9; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .card {{ border: 1px solid #dce4ec; border-radius: 8px; padding: 20px 22px; background: #fff; }}
    table {{ width: 100%; border-collapse: collapse; margin: 14px 0 24px; font-size: 16px; }}
    th, td {{ border: 1px solid #dce4ec; padding: 10px 12px; text-align: left; vertical-align: top; }}
    th {{ background: #edf3f8; }}
    figure {{ margin: 28px 0; }}
    img {{ width: 100%; max-width: 1000px; display: block; border: 1px solid #dce4ec; border-radius: 8px; }}
    figcaption, .muted {{ color: #5f6f80; font-size: 16px; }}
    .formula {{ white-space: pre-wrap; background: #f1f4f7; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <p>V9 formal extension of V8</p>
    <h1>把“诚实偏置”扩成一个干净的主实验</h1>
    <p class="lead">V9 不再只问模型是否更信诚实对象，而是系统地区分 factual honesty、真实返还政策、呈现方式和几类语言/事实 control。</p>
  </header>

  <section>
    <h2>当前状态</h2>
    <p>{html.escape(result_status)}</p>
    <div class="grid">
      <div class="card"><h3>主设计</h3><p><code>2 factual honesty × 2 return policy × 2 presentation × 2 orthogonality</code>。</p></div>
      <div class="card"><h3>关键 controls</h3><p><code>no-statement</code>、<code>irrelevant-truth</code>、<code>cheap-talk-only</code>。</p></div>
      <div class="card"><h3>主因变量</h3><p><code>investment</code>，也就是每轮真实暴露给 partner 的 token 数。</p></div>
      <div class="card"><h3>收益代价</h3><p><code>payoff_t = 10 - investment_t + returned_tokens_t</code>。</p></div>
    </div>
  </section>

  <section>
    <h2>为什么这样改</h2>
    <p>V8 的核心现象很有意思：低诚实对象即使返还政策相同，仍然让模型投得更少，并因此少拿收益。但 V8 还可能被质疑：模型是不是只是把真假反馈当成普通正负反馈？是不是因为 prompt 没讲清楚 card truth 与 return policy 无关？是不是 evidence-only 条件让模型进入“找隐藏规则”的做题模式？</p>
    <p>V9 因此把原问题拆成正式主实验：在同一套逐轮投资任务中，同时操纵诚实性和返还政策，并加入三类 control。这样如果 honesty effect 仍然存在，它就不再只是 V8 的偶然现象，而更像模型把可核验诚实性当作合作价值线索的稳定倾向。</p>
  </section>

  <section>
    <h2>实验条件</h2>
    {html_table(planned, ["block", "purpose", "runs", "trial_decisions"])}
    <h3>Return policy</h3>
    {html_table(design["return_policies"], ["return_policy", "label", "description"])}
  </section>

  <section>
    <h2>每个 trial 怎么跑</h2>
    <ol>
      <li>模型看到当前 trial 编号和 pre-decision cue。cue 可以是 Alex 的可核验陈述、无陈述、无验证漂亮话，或明确无关的事实陈述。</li>
      <li>模型只输出一个 JSON：<code>{{"investment": 0-10}}</code>。主任务不问 trust、honesty、WTP 或理由。</li>
      <li>脚本计算：投资额被三倍给 Alex，Alex 按预设 return rate 返还 tokens。</li>
      <li>反馈包括当轮投资、返还、payoff；若有可核验陈述，则反馈实际值和是否匹配。</li>
      <li><code>sequential_trial</code> 在同一对话中继续下一轮；<code>evidence_only</code> 每轮独立调用，只给压缩历史 summary。</li>
    </ol>
  </section>

  <section>
    <h2>Evidence-only 怎么修</h2>
    <p>V8 的 evidence-only 失败点在于 history narrative 太像隐藏规则题。V9 改成压缩 JSON summary，只给四类信息：已完成轮数、truth summary、return summary、previous investments / payoffs。它不再逐句复述历史，也不要求模型解释规则。</p>
    <p>Runner 还支持 <code>--response-format-json</code>，如果接口兼容，会在请求里加入 <code>{{"type": "json_object"}}</code>，减少长篇推理和非 JSON 输出。</p>
  </section>

  <section>
    <h2>分析方式</h2>
    <p>均值图只作为描述。正式分析以 trial-level 数据为主，脚本会导出 <code>output/trial_level_data.csv</code>。</p>
    <div class="formula">investment_t ~ cumulative_truth_rate_before + cumulative_return_rate_before
             + previous_payoff + trial
             + statement_mode + return_policy
             + presentation_mode + orthogonality_instruction + model</div>
    <p>Payoff cost 单独报告：如果低诚实条件投资更低，并导致在公平返还对象上少拿收益，这就是模型把 orthogonal honesty cue 当成合作价值代理信号的行为代价。</p>
  </section>

  <section>
    <h2>当前 sequential 完整信号</h2>
    {current_observations(rows, results, summary)}
  </section>

  <section>
    <h2>讨论沉淀与下一步</h2>
    {discussion_takeaways(rows)}
  </section>

  <section>
    <h2>结果图</h2>
    {figs_html}
  </section>

  <section>
    <h2>主实验结果表</h2>
    {html_table(main_summary, ["return_policy", "honesty_level", "presentation_mode", "orthogonality_instruction", "n_trials", "n_runs", "mean_investment", "mean_return_rate", "mean_payoff"])}
    <h2>Control 结果表</h2>
    {html_table(control_summary, ["block", "return_policy", "honesty_level", "presentation_mode", "n_trials", "n_runs", "mean_investment", "mean_return_rate", "mean_payoff"])}
  </section>

  <section>
    <h2>Reviewer 风险点</h2>
    <ul>
      <li>如果 explicit orthogonality 后 bias 消失，说明模型能被规则纠偏；这不是坏结果，但故事要从“稳定偏置”改成“默认泛化，但可被规则约束”。</li>
      <li>如果 irrelevant-truth 也出现同样 bias，说明模型可能不是在建模 partner 的社会诚实性，而是在把任何真假反馈泛化到合作判断。</li>
      <li>如果 no-statement 和 cheap-talk-only 差异很小，说明漂亮话本身仍然弱；这会支持 V1-V4 的主线。</li>
      <li>如果 evidence-only 和 sequential 差异很大，需要解释连续互动上下文是否带来自我一致性或局部 norm carryover。</li>
    </ul>
  </section>
</body>
</html>
"""
    (OUT / "report.html").write_text(report, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    design = read_json(DESIGN_PATH, {})
    runs = read_json(RUN_CONDITIONS_PATH, [])
    results = read_json(RESULTS_PATH, [])
    successful = [item for item in results if not item.get("error")]
    rows = flatten_trials(successful)
    write_trial_csv(rows)

    by_condition = group_means(
        rows,
        ["block", "statement_mode", "honesty_level", "return_policy", "presentation_mode", "orthogonality_instruction"],
    )
    summary = {
        "total_planned_runs": len(runs),
        "completed_runs": len(results),
        "successful_runs": len(successful),
        "trial_rows": len(rows),
        "by_condition": by_condition,
        "diagnostic_correlations": diagnostic_correlations(rows),
        "analysis_formula": design.get("analysis_plan", {}).get("trial_level_model"),
        "payoff_definition": design.get("analysis_plan", {}).get("payoff_definition"),
    }
    write_json(OUT / "summary.json", summary)
    figure_paths = plot_main(rows)
    make_report(design, runs, results, rows, summary, figure_paths)
    print(f"Wrote {OUT / 'summary.json'}")
    print(f"Wrote {OUT / 'report.html'}")
    if rows:
        print(f"Wrote {OUT / 'trial_level_data.csv'}")


if __name__ == "__main__":
    main()
