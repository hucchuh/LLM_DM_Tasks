from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
DATA = OUT / "trial_level_data.csv"


def read_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with DATA.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row: dict[str, Any] = dict(raw)
            for key in [
                "run_id",
                "seed_index",
                "trial",
                "investment",
                "returned_tokens",
                "payoff",
                "net_gain_from_investment",
            ]:
                row[key] = int(float(row[key])) if row[key] != "" else None
            for key in [
                "return_rate",
                "cumulative_truth_rate_before",
                "cumulative_return_rate_before",
                "previous_payoff",
            ]:
                row[key] = float(row[key]) if row[key] != "" else None
            rows.append(row)
    return rows


def zscore(values: list[float | None]) -> list[float | None]:
    present = [value for value in values if value is not None]
    mu = sum(present) / len(present)
    sd = math.sqrt(sum((value - mu) ** 2 for value in present) / (len(present) - 1))
    if sd == 0:
        return [0.0 if value is not None else None for value in values]
    return [((value - mu) / sd) if value is not None else None for value in values]


def add_standardized(rows: list[dict[str, Any]], columns: list[str]) -> None:
    for col in columns:
        scores = zscore([row[col] for row in rows])
        for row, score in zip(rows, scores):
            row[f"{col}_z"] = score


def normal_pvalue(t_value: float) -> float:
    cdf = 0.5 * (1.0 + math.erf(abs(t_value) / math.sqrt(2.0)))
    return max(0.0, min(1.0, 2.0 * (1.0 - cdf)))


def ols_cluster(
    rows: list[dict[str, Any]],
    predictors: list[tuple[str, Any]],
    outcome: str = "investment",
    cluster_key: str = "run_id",
) -> dict[str, Any]:
    kept = []
    x_rows = []
    y_vals = []
    for row in rows:
        values = [1.0]
        ok = row[outcome] is not None
        for _, fn in predictors:
            value = fn(row)
            if value is None:
                ok = False
                break
            values.append(float(value))
        if ok:
            kept.append(row)
            x_rows.append(values)
            y_vals.append(float(row[outcome]))

    x = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_vals, dtype=float)
    names = ["Intercept"] + [name for name, _ in predictors]
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    n, k = x.shape

    clusters: dict[Any, list[int]] = defaultdict(list)
    for idx, row in enumerate(kept):
        clusters[row[cluster_key]].append(idx)

    meat = np.zeros((k, k), dtype=float)
    for indices in clusters.values():
        xg = x[indices, :]
        eg = resid[indices]
        score = xg.T @ eg
        meat += np.outer(score, score)

    g = len(clusters)
    correction = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = correction * xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    t_values = beta / se

    coef_rows = []
    for name, b, s, t in zip(names, beta, se, t_values):
        coef_rows.append(
            {
                "term": name,
                "coef": round(float(b), 4),
                "cluster_se": round(float(s), 4),
                "t": round(float(t), 3) if math.isfinite(float(t)) else None,
                "p_normal_approx": round(normal_pvalue(float(t)), 4) if math.isfinite(float(t)) else None,
            }
        )

    sst = float(np.sum((y - np.mean(y)) ** 2))
    sse = float(np.sum(resid**2))
    return {
        "n": n,
        "clusters": g,
        "r2": round(1 - sse / sst, 4) if sst else None,
        "terms": coef_rows,
    }


def term(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in rows:
        if row["term"] == name:
            return row
    raise KeyError(name)


def html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>暂无结果。</p>"
    cols = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(col)}</th>" for col in cols)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row[col]))}</td>" for col in cols) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def explicit_gap_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    target = [
        row
        for row in rows
        if row["block"] == "main_partner_honesty"
        and row["return_policy"] == "fair_high"
        and row["orthogonality_instruction"] == "explicit_orthogonality"
    ]
    by_seed: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in target:
        by_seed[int(row["seed_index"])][row["honesty_level"]].append(row)

    paired = []
    for seed, groups in sorted(by_seed.items()):
        if "high" not in groups or "low" not in groups:
            continue
        high_inv = [row["investment"] for row in groups["high"]]
        low_inv = [row["investment"] for row in groups["low"]]
        high_early = [row["investment"] for row in groups["high"] if int(row["trial"]) <= 6]
        low_early = [row["investment"] for row in groups["low"] if int(row["trial"]) <= 6]
        high_late = [row["investment"] for row in groups["high"] if int(row["trial"]) >= 13]
        low_late = [row["investment"] for row in groups["low"] if int(row["trial"]) >= 13]
        paired.append(
            {
                "seed": seed,
                "high_mean": round(sum(high_inv) / len(high_inv), 3),
                "low_mean": round(sum(low_inv) / len(low_inv), 3),
                "low_minus_high": round(sum(low_inv) / len(low_inv) - sum(high_inv) / len(high_inv), 3),
                "early_low_minus_high": round(sum(low_early) / len(low_early) - sum(high_early) / len(high_early), 3),
                "late_low_minus_high": round(sum(low_late) / len(low_late) - sum(high_late) / len(high_late), 3),
                "high_zero_trials": sum(1 for item in high_inv if item == 0),
                "low_zero_trials": sum(1 for item in low_inv if item == 0),
            }
        )

    diffs = [row["low_minus_high"] for row in paired]
    sign_p = 2 * (0.5 ** len(diffs)) if diffs and all(item > 0 for item in diffs) else None
    return {
        "paired_seed_differences": paired,
        "mean_low_minus_high": round(sum(diffs) / len(diffs), 3) if diffs else None,
        "sign_test_p_two_sided": round(sign_p, 5) if sign_p is not None else None,
    }


def v9b_gaps() -> list[dict[str, Any]]:
    path = ROOT.parent / "v9b_instruction_control" / "output" / "summary.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("high_low_gaps", [])
    except json.JSONDecodeError:
        return []


def make_report(results: dict[str, Any]) -> None:
    tracker = results["models"]["main_tracker"]
    categorical = results["models"]["main_instruction_categorical"]
    all_tracker = results["models"]["all_conditions_tracker"]
    tracker_terms = tracker["terms"]
    categorical_terms = categorical["terms"]

    prev = term(tracker_terms, "previous_payoff_z")
    ret = term(tracker_terms, "cumulative_return_rate_before_z")
    truth = term(tracker_terms, "cumulative_truth_rate_before_z")
    low = term(categorical_terms, "low_honesty")
    low_exp = term(categorical_terms, "low_honesty × explicit_orthogonality")
    diagnostics = results.get("explicit_gap_diagnostics", {})
    paired_rows = diagnostics.get("paired_seed_differences", [])
    gap_rows = v9b_gaps()
    gap_table = html_table(gap_rows) if gap_rows else "<p>V9b 结果尚未生成。</p>"

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V9 Trial-Level Model</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f7f8fa; }}
    header {{ background: #17375e; color: white; padding: 48px 6vw; }}
    h1 {{ font-size: 48px; margin: 0 0 14px; letter-spacing: 0; }}
    h2 {{ font-size: 28px; margin-top: 0; }}
    p, li {{ font-size: 18px; line-height: 1.75; }}
    section {{ max-width: 1120px; margin: 0 auto; padding: 38px 6vw; background: white; border-bottom: 1px solid #e6ebf0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0 28px; font-size: 15px; }}
    th, td {{ border: 1px solid #d9e1ea; padding: 9px 10px; text-align: left; }}
    th {{ background: #eef3f8; }}
    code {{ background: #eef2f6; padding: 2px 6px; border-radius: 5px; }}
    .note {{ color: #5c6c7d; }}
  </style>
</head>
<body>
  <header>
    <h1>V9 trial-level model</h1>
    <p>用现有 sequential 数据检验：模型投资主要由 payoff、return history、truth history，还是 instruction 驱动。</p>
  </header>

  <section>
    <h2>结论先行</h2>
    <ul>
      <li><strong>previous payoff 是最稳的 trial-level predictor。</strong> 在 main partner 条件中，标准化系数 {prev['coef']}，cluster SE {prev['cluster_se']}。</li>
      <li><strong>cumulative return 也有正向作用。</strong> 标准化系数 {ret['coef']}，cluster SE {ret['cluster_se']}。</li>
      <li><strong>cumulative truth 本身不稳定。</strong> 标准化系数 {truth['coef']}，接近 0。这和总相关 <code>r=-0.031</code> 一致。</li>
      <li><strong>instruction 会重写 honesty effect。</strong> categorical model 里，<code>low_honesty</code> 系数 {low['coef']}；<code>low_honesty × explicit_orthogonality</code> 系数 {low_exp['coef']}。这说明 explicit orthogonality 不是中性说明，更像一种 causal-rule cue。</li>
    </ul>
    <p class="note">p 值为正态近似，标准误按 run_id 聚类。这个报告用于快速机制判断，不替代之后更正式的混合效应模型。</p>
  </section>

  <section>
    <h2>如何理解 explicit 反转</h2>
    <p>这里的关键不是“低诚实更可信”，而是 explicit orthogonality instruction 改变了模型的任务表征。原始提示词中的关键句是：</p>
    <p><code>Important rule: the truth or falsehood of the pre-decision statement has no causal relation to the partner's return policy. Return behavior is generated independently of statement truth.</code></p>
    <p>这句话可能起到类似 causal / de-biasing cue 的作用：它让模型停止把陈述真假当作合作性的社会证据，转而把任务看成一个需要通过投资来学习的收益过程。</p>
    <p>需要特别区分两个概念：V9 控制的是 <code>return_rate_t</code> 或 return policy，而不是 realized payoff。真正拿到的 <code>payoff_t = 10 - investment_t + returned_tokens_t</code> 会被模型自己的投资额影响。因此早期投资差异会产生反馈回路：早投一点并赚钱，就更容易继续投；一直投 0，就永远看不到正收益证据。</p>
    <p>在 <code>fair/high + explicit</code> 里，low-honesty 相比 high-honesty 的平均投资差为 {html.escape(str(diagnostics.get('mean_low_minus_high')))}；6 个 paired seeds 全部同方向，简单 sign test 双侧 p = {html.escape(str(diagnostics.get('sign_test_p_two_sided')))}。所以它不像单个 outlier，但仍可能是 early exploration / no-learning trap 被放大的路径效应。</p>
    {html_table(paired_rows)}
  </section>

  <section>
    <h2>V9b instruction-control</h2>
    <p>为了检验 explicit 反转是不是“多了一段正式说明”造成的，我们补了 attention-control：它同样增加一段正式说明，但不提 truth 与 return 的因果无关。结果显示 natural 和 attention-control 都是正向 high-low gap，而 explicit orthogonality 是强反向 gap。</p>
    {gap_table}
    <p>这支持一个更精确的解释：反转主要来自 instruction 的因果内容，而不是 prompt 长度或正式语气本身。</p>
  </section>

  <section>
    <h2>讨论沉淀与 next step</h2>
    <p>Forced exploration 不是直接证明 risk-seeking 的工具。它更像一个必要的清洁步骤：先排除“早期不投资导致没有收益证据，从而形成 no-learning trap”这个朴素解释。</p>
    <p>更干净的下一版可以让前 3 轮固定投资 5，或者给两组同样的外生 payoff observation，然后只分析第 4 轮之后的自由投资。如果 forced phase 后 explicit 低诚实优势消失，说明 V9 的反转主要是早期探索差异被 payoff feedback 放大；如果优势仍然存在，才更支持“low honesty + explicit orthogonality 改变了模型的 exploration / risk attitude”。</p>
    <p>更严格的参数模型可以写成 causal-gated reinforcement learning：投资由预期返还 <code>μ_t</code>、诚实信念 <code>h_t</code>、honesty 的因果诊断权重 <code>d_t</code>、探索 bonus 和风险厌恶共同决定。最关键的待检验参数是 <code>β_X</code>：在 explicit 条件下，低诚实是否额外提高探索倾向。</p>
  </section>

  <section>
    <h2>Model 1: main partner tracker</h2>
    <p>只看 <code>main_partner_honesty</code>，并排除没有 lag history 的第 1 轮。连续变量做 z-score。</p>
    <p><code>investment ~ previous_payoff + cumulative_return + cumulative_truth + trial + low_honesty + unfair_low + explicit_orthogonality</code></p>
    <p>n={tracker['n']}, clusters={tracker['clusters']}, R2={tracker['r2']}</p>
    {html_table(tracker_terms)}
  </section>

  <section>
    <h2>Model 2: instruction contrast</h2>
    <p>这个模型专门看做不做 explicit orthogonality instruction 是否改变 high/low honesty contrast。</p>
    <p><code>investment ~ low_honesty × explicit_orthogonality + low_honesty × unfair_low + explicit_orthogonality × unfair_low + trial</code></p>
    <p>n={categorical['n']}, clusters={categorical['clusters']}, R2={categorical['r2']}</p>
    {html_table(categorical_terms)}
  </section>

  <section>
    <h2>Model 3: all-condition tracker</h2>
    <p>把 no-statement、irrelevant-truth、cheap-talk-only 也放进来，检验 overall tracking。truth history 对没有可核验陈述的条件不适用，因此这个模型不放 cumulative truth。</p>
    <p>n={all_tracker['n']}, clusters={all_tracker['clusters']}, R2={all_tracker['r2']}</p>
    {html_table(all_tracker['terms'])}
  </section>
</body>
</html>
"""
    (OUT / "model_report.html").write_text(report, encoding="utf-8")


def main() -> None:
    rows = read_rows()
    rows = [row for row in rows if row["presentation_mode"] == "sequential_trial"]
    add_standardized(rows, ["previous_payoff", "cumulative_return_rate_before", "cumulative_truth_rate_before", "trial"])

    lagged = [row for row in rows if row["previous_payoff"] is not None and row["cumulative_return_rate_before"] is not None]
    main_rows = [
        row
        for row in lagged
        if row["block"] == "main_partner_honesty" and row["cumulative_truth_rate_before"] is not None
    ]

    tracker_predictors = [
        ("previous_payoff_z", lambda r: r["previous_payoff_z"]),
        ("cumulative_return_rate_before_z", lambda r: r["cumulative_return_rate_before_z"]),
        ("cumulative_truth_rate_before_z", lambda r: r["cumulative_truth_rate_before_z"]),
        ("trial_z", lambda r: r["trial_z"]),
        ("low_honesty", lambda r: 1 if r["honesty_level"] == "low" else 0),
        ("unfair_low", lambda r: 1 if r["return_policy"] == "unfair_low" else 0),
        ("explicit_orthogonality", lambda r: 1 if r["orthogonality_instruction"] == "explicit_orthogonality" else 0),
    ]
    categorical_predictors = [
        ("trial_z", lambda r: r["trial_z"]),
        ("low_honesty", lambda r: 1 if r["honesty_level"] == "low" else 0),
        ("unfair_low", lambda r: 1 if r["return_policy"] == "unfair_low" else 0),
        ("explicit_orthogonality", lambda r: 1 if r["orthogonality_instruction"] == "explicit_orthogonality" else 0),
        (
            "low_honesty × explicit_orthogonality",
            lambda r: (1 if r["honesty_level"] == "low" else 0)
            * (1 if r["orthogonality_instruction"] == "explicit_orthogonality" else 0),
        ),
        (
            "low_honesty × unfair_low",
            lambda r: (1 if r["honesty_level"] == "low" else 0)
            * (1 if r["return_policy"] == "unfair_low" else 0),
        ),
        (
            "explicit_orthogonality × unfair_low",
            lambda r: (1 if r["orthogonality_instruction"] == "explicit_orthogonality" else 0)
            * (1 if r["return_policy"] == "unfair_low" else 0),
        ),
        (
            "low_honesty × explicit_orthogonality × unfair_low",
            lambda r: (1 if r["honesty_level"] == "low" else 0)
            * (1 if r["orthogonality_instruction"] == "explicit_orthogonality" else 0)
            * (1 if r["return_policy"] == "unfair_low" else 0),
        ),
    ]
    all_predictors = [
        ("previous_payoff_z", lambda r: r["previous_payoff_z"]),
        ("cumulative_return_rate_before_z", lambda r: r["cumulative_return_rate_before_z"]),
        ("trial_z", lambda r: r["trial_z"]),
        ("unfair_low", lambda r: 1 if r["return_policy"] == "unfair_low" else 0),
        ("main_partner_honesty", lambda r: 1 if r["block"] == "main_partner_honesty" else 0),
        ("irrelevant_truth_control", lambda r: 1 if r["block"] == "irrelevant_truth_control" else 0),
        ("cheap_talk_only_control", lambda r: 1 if r["block"] == "cheap_talk_only_control" else 0),
        ("explicit_orthogonality", lambda r: 1 if r["orthogonality_instruction"] == "explicit_orthogonality" else 0),
    ]

    results = {
        "data_file": str(DATA),
        "explicit_gap_diagnostics": explicit_gap_diagnostics(rows),
        "models": {
            "main_tracker": ols_cluster(main_rows, tracker_predictors),
            "main_instruction_categorical": ols_cluster(main_rows, categorical_predictors),
            "all_conditions_tracker": ols_cluster(lagged, all_predictors),
        },
    }
    (OUT / "model_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    make_report(results)
    print(f"Wrote {OUT / 'model_results.json'}")
    print(f"Wrote {OUT / 'model_report.html'}")


if __name__ == "__main__":
    main()
