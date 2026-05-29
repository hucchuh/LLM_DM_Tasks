from __future__ import annotations

import csv
import html
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
OUT = ROOT / "output"
V9_ROOT = REPO / "Rep_games" / "v9_honesty_source_control"
V9_MODEL = V9_ROOT / "scripts" / "model_v9.py"


spec = importlib.util.spec_from_file_location("v9_model", V9_MODEL)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load V9 model helpers.")
v9_model = importlib.util.module_from_spec(spec)
sys.modules["v9_model"] = v9_model
spec.loader.exec_module(v9_model)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_run(run: dict[str, Any], instruction_type: str, source: str) -> list[dict[str, Any]]:
    rows = []
    for trial in run.get("trial_results", []):
        rows.append(
            {
                "source": source,
                "run_id": f"{source}_{run['run_id']}",
                "numeric_run_id": run["run_id"],
                "model": run.get("model"),
                "instruction_type": instruction_type,
                "honesty_level": run["honesty_level"],
                "return_policy": run["return_policy"],
                "trial": int(trial["trial"]),
                "statement_true": trial["statement_true"],
                "investment": int(trial["investment"]),
                "payoff": int(trial["payoff"]),
                "previous_payoff": trial.get("previous_payoff"),
                "cumulative_return_rate_before": trial.get("cumulative_return_rate_before"),
                "cumulative_truth_rate_before": trial.get("cumulative_truth_rate_before"),
            }
        )
    return rows


def load_rows() -> list[dict[str, Any]]:
    rows = []
    v9_results = read_json(V9_ROOT / "output" / "results.json", [])
    for run in v9_results:
        if run.get("error"):
            continue
        if run["block"] != "main_partner_honesty":
            continue
        if run["presentation_mode"] != "sequential_trial":
            continue
        if run["return_policy"] != "fair_high":
            continue
        if run["orthogonality_instruction"] == "standard":
            rows.extend(flatten_run(run, "natural", "v9"))
        elif run["orthogonality_instruction"] == "explicit_orthogonality":
            rows.extend(flatten_run(run, "explicit_orthogonality", "v9"))

    v9b_results = read_json(OUT / "results.json", [])
    for run in v9b_results:
        if run.get("error"):
            continue
        rows.extend(flatten_run(run, "attention_control", "v9b"))
    return rows


def group_summary(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row[key] for key in keys)].append(row)
    out = []
    for key, items in sorted(buckets.items()):
        out.append(
            {
                **dict(zip(keys, key)),
                "n_runs": len({item["run_id"] for item in items}),
                "n_trials": len(items),
                "mean_investment": round(mean(item["investment"] for item in items), 3),
                "mean_payoff": round(mean(item["payoff"] for item in items), 3),
            }
        )
    return out


def high_low_gaps(condition_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    by_instruction: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in condition_summary:
        by_instruction[row["instruction_type"]][row["honesty_level"]] = row
    for instruction, values in sorted(by_instruction.items()):
        if "high" not in values or "low" not in values:
            continue
        high = values["high"]
        low = values["low"]
        out.append(
            {
                "instruction_type": instruction,
                "high_investment": high["mean_investment"],
                "low_investment": low["mean_investment"],
                "high_minus_low": round(high["mean_investment"] - low["mean_investment"], 3),
                "high_payoff": high["mean_payoff"],
                "low_payoff": low["mean_payoff"],
                "payoff_gap": round(high["mean_payoff"] - low["mean_payoff"], 3),
            }
        )
    return out


def write_csv(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with (OUT / "trial_level_data.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_gaps(gaps: list[dict[str, Any]]) -> str | None:
    if not gaps:
        return None
    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    labels = [row["instruction_type"] for row in gaps]
    values = [row["high_minus_low"] for row in gaps]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#2f6f9f" if value >= 0 else "#d65f59" for value in values]
    ax.bar(labels, values, color=colors)
    ax.axhline(0, color="#2a2a2a", linewidth=1)
    ax.set_ylabel("High honesty - low honesty investment")
    ax.set_title("V9b: instruction changes the honesty gap")
    ax.tick_params(axis="x", labelrotation=15)
    fig.tight_layout()
    path = fig_dir / "honesty_gap_by_instruction.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path.relative_to(OUT).as_posix()


def add_standardized(rows: list[dict[str, Any]], columns: list[str]) -> None:
    for col in columns:
        values = [row[col] for row in rows]
        scores = v9_model.zscore(values)
        for row, score in zip(rows, scores):
            row[f"{col}_z"] = score


def run_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lagged = [row for row in rows if row["previous_payoff"] is not None]
    add_standardized(lagged, ["previous_payoff", "trial"])
    predictors = [
        ("previous_payoff_z", lambda r: r["previous_payoff_z"]),
        ("trial_z", lambda r: r["trial_z"]),
        ("low_honesty", lambda r: 1 if r["honesty_level"] == "low" else 0),
        ("explicit_orthogonality", lambda r: 1 if r["instruction_type"] == "explicit_orthogonality" else 0),
        ("attention_control", lambda r: 1 if r["instruction_type"] == "attention_control" else 0),
        (
            "low_honesty × explicit_orthogonality",
            lambda r: (1 if r["honesty_level"] == "low" else 0)
            * (1 if r["instruction_type"] == "explicit_orthogonality" else 0),
        ),
        (
            "low_honesty × attention_control",
            lambda r: (1 if r["honesty_level"] == "low" else 0)
            * (1 if r["instruction_type"] == "attention_control" else 0),
        ),
    ]
    return v9_model.ols_cluster(lagged, predictors, cluster_key="run_id")


def html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>暂无结果。</p>"
    cols = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(col)}</th>" for col in cols)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row[col]))}</td>" for col in cols) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def make_report(summary: dict[str, Any]) -> None:
    gaps = summary["high_low_gaps"]
    gap_text = {row["instruction_type"]: row["high_minus_low"] for row in gaps}
    fig_html = (
        f"<figure><img src='{html.escape(summary['figure'])}'><figcaption>High-low honesty gap by instruction.</figcaption></figure>"
        if summary.get("figure")
        else "<p>暂无图。</p>"
    )

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V9b Instruction-Control</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f6f7f9; }}
    header {{ background: #17375e; color: white; padding: 48px 6vw; }}
    h1 {{ font-size: 48px; margin: 0 0 14px; letter-spacing: 0; }}
    h2 {{ font-size: 28px; margin-top: 0; }}
    p, li {{ font-size: 18px; line-height: 1.75; }}
    section {{ max-width: 1120px; margin: 0 auto; padding: 38px 6vw; background: white; border-bottom: 1px solid #e6ebf0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0 28px; font-size: 15px; }}
    th, td {{ border: 1px solid #d9e1ea; padding: 9px 10px; text-align: left; }}
    th {{ background: #eef3f8; }}
    img {{ width: 100%; max-width: 900px; border: 1px solid #d9e1ea; border-radius: 8px; }}
    code {{ background: #eef2f6; padding: 2px 6px; border-radius: 5px; }}
  </style>
</head>
<body>
  <header>
    <h1>V9b: instruction-control test</h1>
    <p>检验 explicit orthogonality 是中性规则说明，还是一种会改变任务表征的 causal cue。</p>
  </header>
  <section>
    <h2>核心结果</h2>
    <ul>
      <li><code>natural</code> high-low gap = {html.escape(str(gap_text.get('natural')))}。</li>
      <li><code>explicit_orthogonality</code> high-low gap = {html.escape(str(gap_text.get('explicit_orthogonality')))}。</li>
      <li><code>attention_control</code> high-low gap = {html.escape(str(gap_text.get('attention_control')))}。</li>
    </ul>
    <p><strong>结果支持 instruction-content explanation。</strong> Attention-control 和 natural 都是正向 high-low gap，而 explicit orthogonality 是强反向 gap。这说明 V9 中 explicit condition 的反转不太可能只是因为“多了一段正式说明”或“prompt 更长”，更可能是因为“truth 与 return 无因果关系”这句话把模型推入了 causal-rule-following mode。</p>
    <p>换句话说，explicit orthogonality 更像一种 causal / de-biasing cue，而不是中性的实验说明。它会改变模型如何表征任务，而不只是提供背景信息。</p>
  </section>
  <section>
    <h2>High-low gap</h2>
    {fig_html}
    {html_table(gaps)}
  </section>
  <section>
    <h2>Condition means</h2>
    {html_table(summary['condition_summary'])}
  </section>
  <section>
    <h2>Trial-level model</h2>
    <p><code>investment ~ previous_payoff + trial + low_honesty * instruction_type</code>，标准误按 run_id 聚类。</p>
    <p>n={summary['model']['n']}, clusters={summary['model']['clusters']}, R2={summary['model']['r2']}</p>
    {html_table(summary['model']['terms'])}
  </section>
</body>
</html>
"""
    (OUT / "report.html").write_text(report, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    write_csv(rows)
    condition_summary = group_summary(rows, ["instruction_type", "honesty_level"])
    gaps = high_low_gaps(condition_summary)
    figure = plot_gaps(gaps)
    model = run_model(rows) if rows else {}
    summary = {
        "n_trials": len(rows),
        "n_runs": len({row["run_id"] for row in rows}),
        "condition_summary": condition_summary,
        "high_low_gaps": gaps,
        "model": model,
        "figure": figure,
    }
    write_json(OUT / "summary.json", summary)
    make_report(summary)
    print(f"Wrote {OUT / 'summary.json'}")
    print(f"Wrote {OUT / 'report.html'}")
    print(f"Wrote {OUT / 'trial_level_data.csv'}")


if __name__ == "__main__":
    main()
