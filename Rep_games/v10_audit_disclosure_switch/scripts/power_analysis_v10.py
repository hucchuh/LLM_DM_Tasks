from __future__ import annotations

import argparse
import csv
import html
import itertools
import json
import math
import random
from pathlib import Path
from statistics import mean, stdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            row["seed_index"] = int(row["seed_index"])
            row["investment"] = float(row["investment"])
            row["payoff"] = float(row["payoff"])
            rows.append(row)
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def normal_p_two_sided(z: float) -> float:
    return 2 * (1 - normal_cdf(abs(z)))


def seed_mean(rows: list[dict[str, Any]], seed: int, midpoint: str, honesty: str, phase: str) -> float | None:
    vals = [
        row["investment"]
        for row in rows
        if row["seed_index"] == seed
        and row["midpoint_message"] == midpoint
        and row["honesty_level"] == honesty
        and row["phase"] == phase
    ]
    return mean(vals) if vals else None


def seed_level_did(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for seed in sorted({row["seed_index"] for row in rows}):
        values = {}
        complete = True
        for midpoint in ["neutral_reminder", "orthogonality_disclosure"]:
            for phase in ["pre", "post"]:
                high = seed_mean(rows, seed, midpoint, "high", phase)
                low = seed_mean(rows, seed, midpoint, "low", phase)
                if high is None or low is None:
                    complete = False
                    break
                values[(midpoint, phase)] = low - high
            if not complete:
                break
        if complete:
            neutral_change = values[("neutral_reminder", "post")] - values[("neutral_reminder", "pre")]
            orth_change = values[("orthogonality_disclosure", "post")] - values[
                ("orthogonality_disclosure", "pre")
            ]
            out.append(
                {
                    "seed_index": seed,
                    "neutral_pre_low_minus_high": round(values[("neutral_reminder", "pre")], 6),
                    "neutral_post_low_minus_high": round(values[("neutral_reminder", "post")], 6),
                    "orth_pre_low_minus_high": round(values[("orthogonality_disclosure", "pre")], 6),
                    "orth_post_low_minus_high": round(values[("orthogonality_disclosure", "post")], 6),
                    "neutral_change": round(neutral_change, 6),
                    "orth_change": round(orth_change, 6),
                    "did": round(orth_change - neutral_change, 6),
                }
            )
    return out


def signflip_p(values: list[float], sims: int = 200000) -> tuple[float | None, str]:
    n = len(values)
    if not values:
        return None, "none"
    if n > 18:
        rng = random.Random(20260529)
        observed = abs(mean(values))
        count = 0
        for _ in range(sims):
            value = abs(mean([item * (1 if rng.random() < 0.5 else -1) for item in values]))
            if value >= observed - 1e-12:
                count += 1
        return count / sims, f"monte_carlo_{sims}"
    observed = abs(mean(values))
    total = 0
    count = 0
    for signs in itertools.product([-1, 1], repeat=n):
        total += 1
        value = abs(mean([item * sign for item, sign in zip(values, signs)]))
        if value >= observed - 1e-12:
            count += 1
    return count / total, "exact"


def bootstrap_ci(values: list[float], sims: int = 50000) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(20260529)
    boots = []
    n = len(values)
    for _ in range(sims):
        boots.append(mean([values[rng.randrange(n)] for _ in range(n)]))
    boots.sort()
    return [round(boots[int(0.025 * sims)], 4), round(boots[int(0.975 * sims) - 1], 4)]


def one_sample_summary(values: list[float]) -> dict[str, Any]:
    n = len(values)
    m = mean(values) if values else None
    sd = stdev(values) if len(values) > 1 else None
    se = sd / math.sqrt(n) if sd and n else None
    z = m / se if m is not None and se else None
    p_value, p_method = signflip_p(values)
    return {
        "n_seeds": n,
        "mean": round(m, 4) if m is not None else None,
        "sd": round(sd, 4) if sd is not None else None,
        "cohens_dz": round(m / sd, 4) if m is not None and sd else None,
        "z_or_large_sample_t": round(z, 4) if z is not None else None,
        "normal_p_two_sided": round(normal_p_two_sided(z), 4) if z is not None else None,
        "signflip_p_two_sided": round(p_value, 4) if p_value is not None else None,
        "signflip_method": p_method,
        "bootstrap_95ci": bootstrap_ci(values),
    }


def required_n(effect_mean: float, effect_sd: float, target_power: float) -> int | None:
    if effect_sd <= 0 or effect_mean == 0:
        return None
    z_alpha = 1.96
    z_power = {0.8: 0.842, 0.9: 1.282, 0.95: 1.645}[target_power]
    dz = abs(effect_mean / effect_sd)
    return math.ceil(((z_alpha + z_power) / dz) ** 2)


def monte_carlo_power(values: list[float], n: int, sims: int, rng: random.Random) -> float:
    if not values:
        return float("nan")
    hits = 0
    for _ in range(sims):
        sample = [values[rng.randrange(len(values))] for _ in range(n)]
        sd = stdev(sample) if len(sample) > 1 else 0
        if sd <= 0:
            continue
        z = mean(sample) / (sd / math.sqrt(n))
        if normal_p_two_sided(z) < 0.05:
            hits += 1
    return hits / sims


def html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>暂无结果。</p>"
    cols = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(col)}</th>" for col in cols)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row[col]))}</td>" for col in cols) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def make_report(output_dir: Path, result: dict[str, Any]) -> None:
    rows = result["power_curve"]
    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V10 seed-level power analysis</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; color: #172033; background: #f5f7fa; }}
    header {{ background: #17375e; color: white; padding: 44px 6vw; }}
    section {{ max-width: 1100px; margin: 0 auto; padding: 34px 6vw; background: white; border-bottom: 1px solid #dfe6ef; }}
    h1 {{ font-size: 44px; margin: 0 0 12px; }}
    h2 {{ font-size: 28px; margin: 0 0 12px; }}
    p, li {{ font-size: 18px; line-height: 1.75; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0 28px; font-size: 15px; }}
    th, td {{ border: 1px solid #dfe6ef; padding: 9px 10px; text-align: left; }}
    th {{ background: #eef3f8; }}
    code {{ background: #edf1f5; padding: 2px 6px; border-radius: 5px; }}
  </style>
</head>
<body>
  <header>
    <h1>V10 seed-level power analysis</h1>
    <p>分析单位是 seed/run，而不是单个 trial。核心效应是 V10 的 difference-in-differences。</p>
  </header>
  <section>
    <h2>当前效应</h2>
    <p>当前完整 paired seeds: <strong>{result['did_summary']['n_seeds']}</strong>。DID 均值为 <strong>{result['did_summary']['mean']}</strong>，seed-level SD 为 <strong>{result['did_summary']['sd']}</strong>，dz 为 <strong>{result['did_summary']['cohens_dz']}</strong>。</p>
    {html_table([result['did_summary']])}
  </section>
  <section>
    <h2>样本量估计</h2>
    <p>这是基于当前 seed-level DID 效应大小的近似 power analysis。它用于规划下一轮 API 预算，不应被当成最终功效结论。</p>
    {html_table(result['required_n'])}
  </section>
  <section>
    <h2>Bootstrap power curve</h2>
    {html_table(rows)}
  </section>
  <section>
    <h2>解释</h2>
    <p>如果当前效应大小稳定，V10 的 DID 需要的 seed 数会比较多。原因是每个 seed 的 DID 方差很大：有些 seed 显示 disclosure 释放低诚实惩罚，有些 seed 则反方向。因此，增加同一 run 内 trial 不能替代增加独立 seed。</p>
  </section>
</body>
</html>
"""
    (output_dir / "power_analysis.html").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "output"))
    parser.add_argument("--sims", type=int, default=10000)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    rows = read_rows(output_dir / "trial_level_data.csv")
    seed_rows = seed_level_did(rows)
    did_values = [row["did"] for row in seed_rows]
    did_summary = one_sample_summary(did_values)

    m = mean(did_values)
    sd = stdev(did_values) if len(did_values) > 1 else 0.0
    required = [
        {"target_power": "80%", "required_seeds": required_n(m, sd, 0.8)},
        {"target_power": "90%", "required_seeds": required_n(m, sd, 0.9)},
        {"target_power": "95%", "required_seeds": required_n(m, sd, 0.95)},
    ]

    rng = random.Random(20260529)
    curve = []
    for n in [8, 12, 16, 20, 24, 30, 40, 50, 60, 80, 100, 120]:
        if n < len(did_values):
            continue
        curve.append({"n_seeds": n, "estimated_power": round(monte_carlo_power(did_values, n, args.sims, rng), 3)})

    result = {
        "output_dir": str(output_dir),
        "seed_level_did": seed_rows,
        "did_summary": did_summary,
        "required_n": required,
        "power_curve": curve,
        "method": "Seed-level DID; approximate two-sided alpha=.05 normal/t-style test; bootstrap resampling of observed seed-level effects.",
    }
    write_json(output_dir / "power_analysis.json", result)
    make_report(output_dir, result)
    print(f"Wrote {output_dir / 'power_analysis.json'}")
    print(f"Wrote {output_dir / 'power_analysis.html'}")


if __name__ == "__main__":
    main()
