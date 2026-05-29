from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = OUT / "figures"
RESULTS_PATH = OUT / "results.json"


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
        if run.get("error"):
            continue
        for trial in run.get("trial_results", []):
            rows.append(
                {
                    "run_id": run["run_id"],
                    "model": run.get("model"),
                    "seed_index": run["seed_index"],
                    "honesty_level": run["honesty_level"],
                    "midpoint_message": run["midpoint_message"],
                    "phase": trial["phase"],
                    "after_midpoint": trial["after_midpoint"],
                    "choice_trial": trial["choice_trial"],
                    "statement_true": trial["statement_true"],
                    "return_rate": trial["return_rate"],
                    "investment": trial["investment"],
                    "returned_tokens": trial["returned_tokens"],
                    "payoff": trial["payoff"],
                    "net_gain_from_investment": trial["net_gain_from_investment"],
                    "truth_belief_before": trial.get("truth_belief_before"),
                    "return_belief_before": trial.get("return_belief_before"),
                    "return_uncertainty_before": trial.get("return_uncertainty_before"),
                    "previous_payoff": trial.get("previous_payoff"),
                }
            )
    return rows


def flatten_probes(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for run in results:
        if run.get("error") or run.get("probe_error"):
            continue
        probe = run.get("final_probe") or {}
        if not probe:
            continue
        required = ["moral_trust", "expected_return_rate", "truth_return_link", "controllability"]
        if any(probe.get(key) is None for key in required):
            continue
        rows.append(
            {
                "run_id": run["run_id"],
                "seed_index": run["seed_index"],
                "honesty_level": run["honesty_level"],
                "midpoint_message": run["midpoint_message"],
                "moral_trust": probe.get("moral_trust"),
                "expected_return_rate": probe.get("expected_return_rate"),
                "truth_return_link": probe.get("truth_return_link"),
                "controllability": probe.get("controllability"),
                "strategy": probe.get("strategy"),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
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
                "mean_investment": round(mean(float(item["investment"]) for item in items), 3),
                "mean_payoff": round(mean(float(item["payoff"]) for item in items), 3),
                "mean_return_rate": round(mean(float(item["return_rate"]) for item in items), 3),
                "truth_rate": round(mean(1.0 if item["statement_true"] else 0.0 for item in items), 3),
            }
        )
    return out


def probe_means(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[(row["midpoint_message"], row["honesty_level"])].append(row)
    out = []
    for (midpoint, honesty), items in sorted(buckets.items()):
        out.append(
            {
                "midpoint_message": midpoint,
                "honesty_level": honesty,
                "n_runs": len(items),
                "moral_trust": round(mean(float(item["moral_trust"]) for item in items), 3),
                "expected_return_rate": round(mean(float(item["expected_return_rate"]) for item in items), 3),
                "truth_return_link": round(mean(float(item["truth_return_link"]) for item in items), 3),
                "controllability": round(mean(float(item["controllability"]) for item in items), 3),
            }
        )
    return out


def mean_filter(rows: list[dict[str, Any]], **filters: Any) -> float | None:
    vals = [float(row["investment"]) for row in rows if all(row.get(k) == v for k, v in filters.items())]
    return round(mean(vals), 3) if vals else None


def payoff_filter(rows: list[dict[str, Any]], **filters: Any) -> float | None:
    vals = [float(row["payoff"]) for row in rows if all(row.get(k) == v for k, v in filters.items())]
    return round(mean(vals), 3) if vals else None


def compute_did(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gap_rows = []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        pre_low = mean_filter(rows, midpoint_message=midpoint, honesty_level="low", phase="pre")
        pre_high = mean_filter(rows, midpoint_message=midpoint, honesty_level="high", phase="pre")
        post_low = mean_filter(rows, midpoint_message=midpoint, honesty_level="low", phase="post")
        post_high = mean_filter(rows, midpoint_message=midpoint, honesty_level="high", phase="post")
        pre_gap = round(pre_low - pre_high, 3) if pre_low is not None and pre_high is not None else None
        post_gap = round(post_low - post_high, 3) if post_low is not None and post_high is not None else None
        change = round(post_gap - pre_gap, 3) if pre_gap is not None and post_gap is not None else None
        gap_rows.append(
            {
                "midpoint_message": midpoint,
                "pre_low_minus_high": pre_gap,
                "post_low_minus_high": post_gap,
                "post_minus_pre_change": change,
            }
        )
    neutral = next(row for row in gap_rows if row["midpoint_message"] == "neutral_reminder")
    disclosure = next(row for row in gap_rows if row["midpoint_message"] == "orthogonality_disclosure")
    did = None
    if neutral["post_minus_pre_change"] is not None and disclosure["post_minus_pre_change"] is not None:
        did = round(disclosure["post_minus_pre_change"] - neutral["post_minus_pre_change"], 3)
    return {"gap_rows": gap_rows, "difference_in_differences": did}


def paired_seed_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            by_seed: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for row in rows:
                if row["midpoint_message"] != midpoint or row["phase"] != phase:
                    continue
                by_seed[int(row["seed_index"])][row["honesty_level"]].append(float(row["investment"]))
            diffs = []
            for seed, groups in sorted(by_seed.items()):
                if "high" not in groups or "low" not in groups:
                    continue
                diffs.append(mean(groups["low"]) - mean(groups["high"]))
            out.append(
                {
                    "midpoint_message": midpoint,
                    "phase": phase,
                    "n_paired_seeds": len(diffs),
                    "mean_low_minus_high": round(mean(diffs), 3) if diffs else None,
                    "positive_seed_count": sum(1 for item in diffs if item > 0),
                    "negative_seed_count": sum(1 for item in diffs if item < 0),
                }
            )
    return out


def pearson(rows: list[dict[str, Any]], x_key: str, y_key: str = "investment") -> dict[str, Any]:
    xs = []
    ys = []
    for row in rows:
        xv = row.get(x_key)
        yv = row.get(y_key)
        if xv is None or yv is None:
            continue
        xs.append(float(xv))
        ys.append(float(yv))
    if len(xs) < 3:
        return {"n": len(xs), "r": None}
    mx = mean(xs)
    my = mean(ys)
    sx = sum((x - mx) ** 2 for x in xs)
    sy = sum((y - my) ** 2 for y in ys)
    if sx == 0 or sy == 0:
        return {"n": len(xs), "r": None}
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sx * sy)
    return {"n": len(xs), "r": round(r, 3)}


def zscores(values: list[float | None]) -> list[float | None]:
    present = [value for value in values if value is not None]
    if not present:
        return [None for _ in values]
    mu = mean(present)
    sd = math.sqrt(sum((value - mu) ** 2 for value in present) / max(1, len(present) - 1))
    if sd == 0:
        return [0.0 if value is not None else None for value in values]
    return [((value - mu) / sd) if value is not None else None for value in values]


def fit_ols(rows: list[dict[str, Any]]) -> dict[str, Any]:
    model_rows = [row.copy() for row in rows]
    for col in ["return_belief_before", "truth_belief_before", "return_uncertainty_before", "previous_payoff"]:
        scores = zscores([None if row[col] is None else float(row[col]) for row in model_rows])
        for row, score in zip(model_rows, scores):
            row[col + "_z"] = score

    predictors: list[tuple[str, Callable[[dict[str, Any]], float | None]]] = [
        ("return_belief_before_z", lambda r: r["return_belief_before_z"]),
        ("truth_belief_before_z", lambda r: r["truth_belief_before_z"]),
        ("return_uncertainty_before_z", lambda r: r["return_uncertainty_before_z"]),
        ("previous_payoff_z", lambda r: r["previous_payoff_z"]),
        ("low_honesty", lambda r: 1.0 if r["honesty_level"] == "low" else 0.0),
        ("post_midpoint", lambda r: 1.0 if r["phase"] == "post" else 0.0),
        ("orthogonality_disclosure", lambda r: 1.0 if r["midpoint_message"] == "orthogonality_disclosure" else 0.0),
        (
            "low_honesty_x_post",
            lambda r: (1.0 if r["honesty_level"] == "low" else 0.0) * (1.0 if r["phase"] == "post" else 0.0),
        ),
        (
            "low_honesty_x_orthogonality",
            lambda r: (1.0 if r["honesty_level"] == "low" else 0.0)
            * (1.0 if r["midpoint_message"] == "orthogonality_disclosure" else 0.0),
        ),
        (
            "post_x_orthogonality",
            lambda r: (1.0 if r["phase"] == "post" else 0.0)
            * (1.0 if r["midpoint_message"] == "orthogonality_disclosure" else 0.0),
        ),
        (
            "low_honesty_x_post_x_orthogonality",
            lambda r: (1.0 if r["honesty_level"] == "low" else 0.0)
            * (1.0 if r["phase"] == "post" else 0.0)
            * (1.0 if r["midpoint_message"] == "orthogonality_disclosure" else 0.0),
        ),
    ]

    x_rows = []
    y_vals = []
    kept = []
    for row in model_rows:
        values = [1.0]
        ok = True
        for _, fn in predictors:
            value = fn(row)
            if value is None:
                ok = False
                break
            values.append(float(value))
        if ok:
            kept.append(row)
            x_rows.append(values)
            y_vals.append(float(row["investment"]))

    x = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_vals, dtype=float)
    names = ["Intercept"] + [name for name, _ in predictors]
    beta = np.linalg.pinv(x.T @ x) @ x.T @ y
    pred = x @ beta
    resid = y - pred
    n, k = x.shape
    sigma2 = float(np.sum(resid**2) / max(1, n - k))
    cov = sigma2 * np.linalg.pinv(x.T @ x)
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    terms = []
    for name, b, s in zip(names, beta, se):
        t = float(b / s) if s > 0 else None
        terms.append(
            {
                "term": name,
                "coef": round(float(b), 4),
                "se": round(float(s), 4),
                "t": round(t, 3) if t is not None and math.isfinite(t) else None,
            }
        )
    sst = float(np.sum((y - np.mean(y)) ** 2))
    sse = float(np.sum(resid**2))
    return {"n": n, "r2": round(1 - sse / sst, 4) if sst else None, "terms": terms}


def make_plots(rows: list[dict[str, Any]], probe_rows: list[dict[str, Any]]) -> list[str]:
    FIG.mkdir(parents=True, exist_ok=True)
    paths = []

    colors = {"high": "#2f6f9f", "low": "#d95f59"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, midpoint in zip(axes, ["neutral_reminder", "orthogonality_disclosure"]):
        for honesty in ["high", "low"]:
            xs = []
            ys = []
            for trial in range(1, 13):
                vals = [
                    float(row["investment"])
                    for row in rows
                    if row["midpoint_message"] == midpoint
                    and row["honesty_level"] == honesty
                    and int(row["choice_trial"]) == trial
                ]
                if vals:
                    xs.append(trial)
                    ys.append(mean(vals))
            ax.plot(xs, ys, marker="o", linewidth=2.5, color=colors[honesty], label=honesty)
        ax.axvline(6.5, color="#4b5563", linestyle="--", linewidth=1.5)
        ax.set_title(midpoint.replace("_", " "))
        ax.set_xlabel("Choice trial")
        ax.set_ylim(0, 10)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Mean investment")
    axes[1].legend(frameon=False)
    fig.suptitle("Investment trajectory before and after midpoint message", fontsize=15)
    fig.tight_layout()
    path = FIG / "investment_trajectory.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path.relative_to(OUT).as_posix())

    phase_summary = group_means(rows, ["midpoint_message", "honesty_level", "phase"])
    labels = []
    values = []
    bar_colors = []
    for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
        for phase in ["pre", "post"]:
            low = next(
                item
                for item in phase_summary
                if item["midpoint_message"] == midpoint and item["honesty_level"] == "low" and item["phase"] == phase
            )
            high = next(
                item
                for item in phase_summary
                if item["midpoint_message"] == midpoint and item["honesty_level"] == "high" and item["phase"] == phase
            )
            labels.append(f"{midpoint.replace('_', ' ')}\n{phase}")
            values.append(low["mean_investment"] - high["mean_investment"])
            bar_colors.append("#7a8f3a" if midpoint == "neutral_reminder" else "#9b5de5")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, values, color=bar_colors)
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_ylabel("Low honesty - high honesty investment")
    ax.set_title("Honesty gap by phase")
    fig.tight_layout()
    path = FIG / "phase_gap.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path.relative_to(OUT).as_posix())

    if probe_rows:
        probe_summary = probe_means(probe_rows)
        labels = [f"{row['midpoint_message'].replace('_', ' ')}\n{row['honesty_level']}" for row in probe_summary]
        trust = [row["moral_trust"] for row in probe_summary]
        link = [row["truth_return_link"] for row in probe_summary]
        x = np.arange(len(labels))
        width = 0.38
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.bar(x - width / 2, trust, width, label="moral trust", color="#2f6f9f")
        ax.bar(x + width / 2, link, width, label="truth-return link", color="#d95f59")
        ax.set_xticks(x, labels, rotation=15, ha="right")
        ax.set_ylim(0, 100)
        ax.set_title("Final probe")
        ax.legend(frameon=False)
        fig.tight_layout()
        path = FIG / "final_probe.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        paths.append(path.relative_to(OUT).as_posix())

    return paths


def html_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
    if not rows:
        return "<p class='muted'>暂无结果。</p>"
    cols = columns or list(rows[0].keys())
    head = "".join(f"<th>{html.escape(col)}</th>" for col in cols)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in cols) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def term(model: dict[str, Any], name: str) -> dict[str, Any]:
    for row in model.get("terms", []):
        if row["term"] == name:
            return row
    return {"term": name, "coef": "", "se": "", "t": ""}


def image(path: str, caption: str) -> str:
    return f"<figure><img src='{html.escape(path)}' alt='figure'><figcaption>{html.escape(caption)}</figcaption></figure>"


def make_report(summary: dict[str, Any], rows: list[dict[str, Any]], probe_rows: list[dict[str, Any]], figures: list[str]) -> None:
    did = summary["difference_in_differences"]
    model = summary["observer_style_model"]
    triple = term(model, "low_honesty_x_post_x_orthogonality")
    prev = term(model, "previous_payoff_z")
    ret = term(model, "return_belief_before_z")
    truth = term(model, "truth_belief_before_z")

    phase_rows = summary["by_phase"]
    gap_rows = did["gap_rows"]
    paired_rows = summary["paired_seed_diagnostics"]
    probe_summary = summary["probe_by_condition"]
    corr = summary["diagnostic_correlations"]
    orthogonality_prompt = (
        "Important rule update: in this task, whether Alex's card statements are true or false is generated "
        "independently of Alex's return behavior. Statement truth is evidence about factual honesty, but it "
        "does not causally determine how many tokens Alex returns."
    )

    fig_html = "\n".join(
        [
            image(
                "figures/investment_trajectory.png",
                "图 1. 每个 choice trial 的平均投资。虚线是中途信息出现的位置。V10 关注的不是总体 high/low honesty 差异，而是中途说明之后 low-high gap 是否发生选择性变化。",
            ),
            image(
                "figures/phase_gap.png",
                "图 2. low honesty 减 high honesty 的投资差。正值表示低诚实对象反而获得更高投资。这个图直接对应 V10 的核心判别量。",
            ),
            image(
                "figures/final_probe.png",
                "图 3. 结束后的显性判断。它用于判断模型是否在显性层面理解 honesty 与 return 的关系，而不是作为逐轮决策输入。",
            ),
        ]
    )
    gap_lookup = {row["midpoint_message"]: row for row in gap_rows}
    neutral_gap = gap_lookup.get("neutral_reminder", {})
    disclosure_gap = gap_lookup.get("orthogonality_disclosure", {})
    neutral_high_pre = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "neutral_reminder" and row["honesty_level"] == "high" and row["phase"] == "pre"
    )
    neutral_low_pre = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "neutral_reminder" and row["honesty_level"] == "low" and row["phase"] == "pre"
    )
    neutral_high_post = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "neutral_reminder" and row["honesty_level"] == "high" and row["phase"] == "post"
    )
    neutral_low_post = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "neutral_reminder" and row["honesty_level"] == "low" and row["phase"] == "post"
    )
    disclosure_high_pre = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "orthogonality_disclosure" and row["honesty_level"] == "high" and row["phase"] == "pre"
    )
    disclosure_low_pre = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "orthogonality_disclosure" and row["honesty_level"] == "low" and row["phase"] == "pre"
    )
    disclosure_high_post = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "orthogonality_disclosure" and row["honesty_level"] == "high" and row["phase"] == "post"
    )
    disclosure_low_post = next(
        row
        for row in phase_rows
        if row["midpoint_message"] == "orthogonality_disclosure" and row["honesty_level"] == "low" and row["phase"] == "post"
    )

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V10 audit-disclosure 实验报告</title>
  <style>
    :root {{
      --ink: #152033;
      --muted: #5f6b7a;
      --line: #dfe6ef;
      --soft: #f5f7fa;
      --blue: #17375e;
      --accent: #9b5de5;
    }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; color: var(--ink); background: #f3f5f7; }}
    header {{ background: linear-gradient(135deg, #11243c, #22537d); color: white; padding: 58px 6vw 64px; }}
    header p {{ max-width: 980px; font-size: 22px; line-height: 1.7; }}
    h1 {{ font-size: clamp(42px, 6vw, 76px); margin: 0 0 20px; letter-spacing: 0; }}
    h2 {{ font-size: 32px; margin: 0 0 16px; }}
    h3 {{ font-size: 22px; margin: 24px 0 8px; }}
    p, li {{ font-size: 18px; line-height: 1.82; }}
    section {{ max-width: 1180px; margin: 0 auto; padding: 42px 6vw; background: white; border-bottom: 1px solid var(--line); }}
    .lead {{ font-size: 20px; color: #27364a; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .card {{ border: 1px solid var(--line); border-radius: 8px; padding: 22px; background: #fff; }}
    .note {{ color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; margin: 18px 0 30px; font-size: 15px; }}
    th, td {{ border: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    code {{ background: #edf1f5; padding: 2px 6px; border-radius: 5px; }}
    pre {{ background: #101827; color: #eef6ff; padding: 18px; border-radius: 8px; overflow-x: auto; font-size: 14px; line-height: 1.6; }}
    figure {{ margin: 26px 0 42px; }}
    img {{ width: 100%; max-width: 1080px; display: block; border: 1px solid var(--line); border-radius: 8px; background: white; }}
    figcaption {{ margin-top: 10px; font-size: 17px; line-height: 1.75; color: #39475a; }}
    .metric {{ font-size: 30px; font-weight: 750; color: var(--blue); margin: 6px 0; }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <p>V10 · MiniMax-M2.7 · audit-learning + disclosure switch</p>
    <h1>不诚实为什么会诱发更高探索？</h1>
    <p>V10 不是简单复刻 V8/V9 的 honesty bias，而是专门检验 V9 的异常现象：当模型被明确告知“陈述真假与返还行为无关”之后，低诚实对象是否会被当成一个更值得试探的对象。</p>
  </header>

  <section>
    <h2>研究问题</h2>
    <p class="lead">前几版实验显示，模型通常能很好追踪实际返还；但是 V9 中出现了一个反直觉结果：在 explicit orthogonality 条件下，低诚实 partner 反而获得更高投资。V10 的问题是：这到底是噪音，还是一种可重复的策略转变？</p>
    <div class="grid">
      <div class="card">
        <h3>核心假设</h3>
        <p>如果中途说明“说真话/说假话与返还无关”之后，低诚实对象的投资相对高诚实对象上升，说明模型可能把“不诚实”从“低信任”中剥离出来，并进入一种试探或探索模式。</p>
      </div>
      <div class="card">
        <h3>关键对照</h3>
        <p>V10 加入 neutral midpoint reminder。这样可以区分：投资变化是因为中途多了一句提示、时间推进，还是因为 orthogonality disclosure 的具体语义内容。</p>
      </div>
    </div>
  </section>

  <section>
    <h2>实验设计</h2>
    <p>每个 run 面对同一个 partner Alex。所有条件下，Alex 的真实返还率序列是 matched 的；差异只来自两个维度：</p>
    <table>
      <thead><tr><th>因子</th><th>水平</th><th>说明</th></tr></thead>
      <tbody>
        <tr><td>factual honesty</td><td>high vs low</td><td>high 条件中 Alex 大多数陈述为真；low 条件中大多数陈述为假。</td></tr>
        <tr><td>midpoint message</td><td>neutral reminder vs orthogonality disclosure</td><td>前者只提醒继续决策；后者明确说明陈述真假与返还行为独立。</td></tr>
        <tr><td>phase</td><td>pre vs post</td><td>这是 run 内变量。前 6 个 choice trial 在中途信息前，后 6 个在中途信息后。</td></tr>
      </tbody>
    </table>
    <p>每个 condition 8 个 yoked seed，共 {summary['successful_runs']}/{summary['total_runs']} 个成功 run，{summary['n_trial_rows']} 个逐轮选择。每个 run 先看 8 个 audit records：系统固定投资 5 tokens，让模型看到同一 partner 的陈述真假和返还结果。随后模型自己做 12 轮逐轮投资。</p>
  </section>

  <section>
    <h2>完整流程</h2>
    <ol>
      <li><strong>Audit 阶段：</strong>模型不做选择，只观察系统过去 8 轮固定投资 5 tokens 后 Alex 的返还。这个阶段用于统一收益证据，避免“模型早期投 0 导致之后学不到返还规律”的自我强化。</li>
      <li><strong>Pre 阶段：</strong>模型做 6 轮真实投资。每轮先看到 Alex 的 card statement，投资后才看到实际 card value、陈述是否为真、返还 tokens 和本轮 payoff。</li>
      <li><strong>Midpoint message：</strong>一半 run 收到 neutral reminder；另一半 run 收到 explicit orthogonality disclosure。</li>
      <li><strong>Post 阶段：</strong>模型继续做 6 轮投资。此时可以观察中途信息是否改变 low/high honesty 的投资差。</li>
      <li><strong>Final probe：</strong>全部行为结束后才问 moral trust、expected return、truth-return link 和 controllability，避免 probe 污染逐轮选择。</li>
    </ol>
  </section>

  <section>
    <h2>主要结果</h2>
    <div class="grid">
      <div class="card">
        <h3>核心 difference-in-differences</h3>
        <div class="metric">{did['difference_in_differences']}</div>
        <p class="note">这是 orthogonality 条件的 low-high gap 前后变化，减去 neutral 条件的同样变化。正值表示 orthogonality disclosure 选择性提高了 low honesty 的相对投资。</p>
      </div>
      <div class="card">
        <h3>三重交互参数</h3>
        <div class="metric">{triple['coef']}</div>
        <p class="note">observer-style regression 中 <code>low_honesty x post x orthogonality</code> 的系数。它是模型化版本的核心判别量。</p>
      </div>
    </div>
    <p class="lead">这轮结果没有完全复现 V9 中“低诚实对象反而高于高诚实对象”的强反转，但支持一个更稳妥的版本：明确说明 honesty 与 return 无关之后，低诚实对象的投资惩罚被释放了一部分。neutral reminder 条件下，low-high gap 从 {neutral_gap.get('pre_low_minus_high')} 变成 {neutral_gap.get('post_low_minus_high')}；orthogonality disclosure 条件下，low-high gap 从 {disclosure_gap.get('pre_low_minus_high')} 变成 {disclosure_gap.get('post_low_minus_high')}。两者相减得到 difference-in-differences = {did['difference_in_differences']}。</p>
    <p>换句话说，V10 目前更像是 <strong>orthogonality release effect</strong>，而不是完整的 low-honesty exploration reversal。模型仍然更信任高诚实对象，但当规则明确指出“陈述真假不决定返还”时，它会明显减少对低诚实对象的行为惩罚。</p>
    <h3>Phase-level 均值</h3>
    {html_table(phase_rows, ['midpoint_message', 'honesty_level', 'phase', 'n_runs', 'n_trials', 'mean_investment', 'mean_payoff', 'mean_return_rate', 'truth_rate'])}
    <h3>Low - high honesty gap</h3>
    {html_table(gap_rows, ['midpoint_message', 'pre_low_minus_high', 'post_low_minus_high', 'post_minus_pre_change'])}
    <h3>Paired seed 诊断</h3>
    {html_table(paired_rows, ['midpoint_message', 'phase', 'n_paired_seeds', 'mean_low_minus_high', 'positive_seed_count', 'negative_seed_count'])}
  </section>

  <section>
    <h2>图示结果</h2>
    {fig_html}
  </section>

  <section>
    <h2>Payoff 与显性判断</h2>
    <p>因为所有条件的返还率序列是 matched 的，payoff 差异主要来自模型自己的投资差异。neutral 条件下，低诚实对象的 post payoff 为 {neutral_low_post['mean_payoff']}，高诚实对象为 {neutral_high_post['mean_payoff']}；orthogonality 条件下，低诚实对象的 post payoff 上升到 {disclosure_low_post['mean_payoff']}，但仍低于高诚实对象的 {disclosure_high_post['mean_payoff']}。</p>
    <p>这说明正交说明确实让低诚实对象获得更多投资和收益，但没有把它提升到高诚实对象之上。这里的代价不是“客观收益率更差”，而是模型仍然保留了对低诚实对象的社会性折扣。</p>
    <h3>Final probe</h3>
    {html_table(probe_summary, ['midpoint_message', 'honesty_level', 'n_runs', 'moral_trust', 'expected_return_rate', 'truth_return_link', 'controllability'])}
  </section>

  <section>
    <h2>Observer-style 参数分析</h2>
    <p>这里的 Bayesian observer 不是假设 LLM 内部真的逐项做贝叶斯计算，而是给我们一个可解释的参照系：模型在每一轮之前可以形成两个 belief，一个关于 Alex 说真话的概率，另一个关于 Alex 返还率的期望。Audit 阶段让 high/low honesty 在 return belief 上尽量一致，而在 truth belief 上分离。</p>
    <table>
      <thead><tr><th>变量</th><th>含义</th><th>当前结果</th></tr></thead>
      <tbody>
        <tr><td>return_belief_before</td><td>根据 audit 和已观察返还形成的返还率信念</td><td>coef={ret['coef']}, se={ret['se']}, t={ret['t']}</td></tr>
        <tr><td>truth_belief_before</td><td>根据 audit 和已验证陈述形成的诚实性信念</td><td>coef={truth['coef']}, se={truth['se']}, t={truth['t']}</td></tr>
        <tr><td>previous_payoff</td><td>上一轮实际收益</td><td>coef={prev['coef']}, se={prev['se']}, t={prev['t']}</td></tr>
        <tr><td>low_honesty x post x orthogonality</td><td>低诚实对象在 orthogonality disclosure 后是否选择性提高投资</td><td>coef={triple['coef']}, se={triple['se']}, t={triple['t']}</td></tr>
      </tbody>
    </table>
    <p>诊断相关：investment 与 previous payoff 的相关为 {corr['investment_vs_previous_payoff']['r']}；与 return belief 的相关为 {corr['investment_vs_return_belief']['r']}；与 truth belief 的相关为 {corr['investment_vs_truth_belief']['r']}。</p>
    <h3>完整模型项</h3>
    {html_table(model['terms'], ['term', 'coef', 'se', 't'])}
  </section>

  <section>
    <h2>如何解读</h2>
    <p>V10 对 V9 的异常结果给出了一个比较冷静的修正。V9 中的 strong reversal 在这里没有完整出现，因此不能直接说“低诚实会诱发更高探索”。更准确的表述是：当收益证据被 audit 阶段控制住以后，orthogonality disclosure 会减弱低诚实带来的投资惩罚。</p>
    <p>这仍然有理论价值。final probe 显示，orthogonality 条件下模型显性报告的 truth-return link 很低，且 high/low honesty 的 expected return rate 很接近；也就是说，模型在显性层面理解了“诚实性与返还无关”。但 moral trust 仍然强烈区分 high 与 low honesty，行为投资也没有完全 equalize。这形成了一个更干净的 dissociation：模型能把返还预期与诚实性分开，却不一定能把社会信任折扣从行为中完全拿掉。</p>
    <p>因此，下一步最值得做的不是继续无差别加样本，而是把这个 release effect 拆成两个候选机制：第一，explicit rule 是否降低了 honesty-to-payoff 的错误泛化；第二，它是否额外提高了对低诚实对象的探索意愿。要区分这两者，需要在下一版加入强制观察/强制探索阶段，或者让模型在 choice 前明确报告每一轮的 expected return，再看行为是否仍然偏离。</p>
  </section>

  <section>
    <h2>提示词示例</h2>
    <h3>Choice prompt</h3>
    <pre>{html.escape((ROOT / 'prompts' / 'choice_prompt.md').read_text(encoding='utf-8'))}</pre>
    <h3>Orthogonality disclosure</h3>
    <pre>{html.escape(orthogonality_prompt)}</pre>
  </section>
</body>
</html>
"""
    (OUT / "report.html").write_text(report, encoding="utf-8")


def main() -> None:
    global OUT, FIG, RESULTS_PATH
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT))
    args = parser.parse_args()
    out_arg = Path(args.output_dir)
    OUT = out_arg if out_arg.is_absolute() else ROOT / out_arg
    FIG = OUT / "figures"
    RESULTS_PATH = OUT / "results.json"

    results = read_json(RESULTS_PATH, [])
    successful = [run for run in results if not run.get("error")]
    rows = flatten_trials(results)
    probe_rows = flatten_probes(results)
    write_csv(OUT / "trial_level_data.csv", rows)
    write_csv(OUT / "final_probe_data.csv", probe_rows)

    by_phase = group_means(rows, ["midpoint_message", "honesty_level", "phase"])
    by_trial = group_means(rows, ["midpoint_message", "honesty_level", "choice_trial"])
    did = compute_did(rows) if rows else {"gap_rows": [], "difference_in_differences": None}
    paired = paired_seed_diagnostics(rows) if rows else []
    probe_summary = probe_means(probe_rows) if probe_rows else []
    diagnostics = {
        "investment_vs_previous_payoff": pearson(rows, "previous_payoff"),
        "investment_vs_return_belief": pearson(rows, "return_belief_before"),
        "investment_vs_truth_belief": pearson(rows, "truth_belief_before"),
    }
    model = fit_ols(rows) if rows else {"n": 0, "r2": None, "terms": []}
    figures = make_plots(rows, probe_rows) if rows else []

    summary = {
        "total_runs": len(results),
        "successful_runs": len(successful),
        "failed_runs": len(results) - len(successful),
        "n_trial_rows": len(rows),
        "n_probe_rows": len(probe_rows),
        "by_phase": by_phase,
        "by_trial": by_trial,
        "difference_in_differences": did,
        "paired_seed_diagnostics": paired,
        "probe_by_condition": probe_summary,
        "diagnostic_correlations": diagnostics,
        "observer_style_model": model,
        "figures": figures,
    }
    write_json(OUT / "summary.json", summary)
    make_report(summary, rows, probe_rows, figures)
    print(f"Wrote {OUT / 'summary.json'}")
    print(f"Wrote {OUT / 'report.html'}")


if __name__ == "__main__":
    main()
