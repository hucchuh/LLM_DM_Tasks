from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REP_GAMES = ROOT.parent
V9_RUNNER = REP_GAMES / "v9_honesty_source_control" / "scripts" / "run_v9.py"
OUT = ROOT / "output"
DESIGN_PATH = ROOT / "conditions" / "design.json"
CHOICE_PROMPT = ROOT / "prompts" / "choice_prompt.md"
FINAL_PROBE_PROMPT = ROOT / "prompts" / "final_probe_prompt.md"

DEFAULT_ENDPOINT = "https://lightingtheword.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"
COLORS = ["blue", "red", "green", "yellow", "purple", "orange"]


spec = importlib.util.spec_from_file_location("v9_runner", V9_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load V9 runner.")
v9 = importlib.util.module_from_spec(spec)
sys.modules["v9_runner"] = v9
spec.loader.exec_module(v9)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def exact_flags(true_count: int, total: int, rng: random.Random) -> list[bool]:
    flags = [True] * true_count + [False] * (total - true_count)
    rng.shuffle(flags)
    return flags


def false_value(actual: int, rng: random.Random) -> int:
    return rng.choice([value for value in range(1, 10) if value != actual])


def clamp_int(value: Any, low: int, high: int) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return max(low, min(high, number))


def clamp_float(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return max(low, min(high, number))


def build_base_rows(rates: list[float], seed: int, phase: str) -> list[dict[str, Any]]:
    rng = random.Random(f"base-{seed}-{phase}")
    rows = []
    shuffled_rates = rates[:]
    rng.shuffle(shuffled_rates)
    for idx, rate in enumerate(shuffled_rates, start=1):
        rows.append(
            {
                "phase": phase,
                "phase_trial": idx,
                "card_color": rng.choice(COLORS),
                "actual_value": rng.randint(1, 9),
                "return_rate": float(rate),
            }
        )
    return rows


def add_statements(
    base_rows: list[dict[str, Any]],
    true_count: int,
    seed: int,
    honesty_level: str,
    phase: str,
) -> list[dict[str, Any]]:
    rng = random.Random(f"truth-{seed}-{honesty_level}-{phase}")
    flags = exact_flags(true_count, len(base_rows), rng)
    rows = []
    for row, is_true in zip(base_rows, flags):
        stated = row["actual_value"] if is_true else false_value(int(row["actual_value"]), rng)
        rows.append({**row, "statement_true": is_true, "stated_value": stated})
    return rows


def apply_payoff(row: dict[str, Any], investment: int) -> dict[str, Any]:
    tripled = investment * 3
    returned = int(round(tripled * float(row["return_rate"])))
    return {
        **row,
        "investment": investment,
        "tripled_investment": tripled,
        "returned_tokens": returned,
        "payoff": 10 - investment + returned,
        "net_gain_from_investment": returned - investment,
        "observed_return_rate": round(returned / tripled, 3) if tripled > 0 else None,
    }


def honesty_spec(design: dict[str, Any], honesty_level: str) -> dict[str, Any]:
    for item in design["honesty_levels"]:
        if item["honesty_level"] == honesty_level:
            return item
    raise KeyError(honesty_level)


def midpoint_spec(design: dict[str, Any], midpoint_message: str) -> dict[str, Any]:
    for item in design["midpoint_messages"]:
        if item["midpoint_message"] == midpoint_message:
            return item
    raise KeyError(midpoint_message)


def build_run(
    design: dict[str, Any],
    run_id: int,
    seed_index: int,
    seed: int,
    honesty_level: str,
    midpoint_message: str,
) -> dict[str, Any]:
    honesty = honesty_spec(design, honesty_level)
    midpoint = midpoint_spec(design, midpoint_message)
    audit_base = build_base_rows([float(x) for x in design["audit_return_rates"]], seed, "audit")
    pre_base = build_base_rows([float(x) for x in design["choice_return_rates"][: design["pre_choice_trials"]]], seed, "pre")
    post_base = build_base_rows([float(x) for x in design["choice_return_rates"][design["pre_choice_trials"] :]], seed, "post")

    audit_rows = add_statements(audit_base, int(honesty["truth_counts"]["audit"]), seed, honesty_level, "audit")
    pre_rows = add_statements(pre_base, int(honesty["truth_counts"]["pre"]), seed, honesty_level, "pre")
    post_rows = add_statements(post_base, int(honesty["truth_counts"]["post"]), seed, honesty_level, "post")

    fixed = int(design["fixed_audit_investment"])
    audit_results = []
    for idx, row in enumerate(audit_rows, start=1):
        audit_results.append(
            apply_payoff(
                {
                    **row,
                    "trial": idx,
                    "choice_trial": None,
                },
                fixed,
            )
        )

    choice_trials = []
    for idx, row in enumerate(pre_rows + post_rows, start=1):
        choice_trials.append(
            {
                **row,
                "trial": idx,
                "choice_trial": idx,
                "midpoint_message_seen": idx > int(design["pre_choice_trials"]),
            }
        )

    return {
        "run_id": run_id,
        "seed_index": seed_index,
        "seed": seed,
        "partner_name": design["partner_name"],
        "honesty_level": honesty_level,
        "honesty_label": honesty["label"],
        "midpoint_message": midpoint_message,
        "midpoint_label": midpoint["label"],
        "midpoint_text": midpoint["message"],
        "audit_trials": int(design["audit_trials"]),
        "pre_choice_trials": int(design["pre_choice_trials"]),
        "post_choice_trials": int(design["post_choice_trials"]),
        "total_choice_trials": int(design["pre_choice_trials"]) + int(design["post_choice_trials"]),
        "fixed_audit_investment": fixed,
        "audit_results": audit_results,
        "choice_trials": choice_trials,
        "audit_truth_rate": round(sum(row["statement_true"] for row in audit_results) / len(audit_results), 3),
        "audit_mean_return_rate": round(sum(row["return_rate"] for row in audit_results) / len(audit_results), 3),
        "choice_mean_return_rate": round(sum(row["return_rate"] for row in choice_trials) / len(choice_trials), 3),
    }


def build_runs(seed: int, seeds_per_cell: int | None = None) -> list[dict[str, Any]]:
    design = read_json(DESIGN_PATH, {})
    reps = int(seeds_per_cell or design["seeds_per_cell"])
    master = random.Random(seed)
    yoked_seeds = [master.randint(1, 1_000_000_000) for _ in range(reps)]
    runs = []
    run_id = 1
    for midpoint in design["midpoint_messages"]:
        for honesty in design["honesty_levels"]:
            for seed_index, local_seed in enumerate(yoked_seeds, start=1):
                runs.append(
                    build_run(
                        design,
                        run_id=run_id,
                        seed_index=seed_index,
                        seed=local_seed,
                        honesty_level=honesty["honesty_level"],
                        midpoint_message=midpoint["midpoint_message"],
                    )
                )
                run_id += 1
    return runs


def statement_text(run: dict[str, Any], trial: dict[str, Any]) -> str:
    return (
        f'{run["partner_name"]} says: "I privately checked the {trial["card_color"]} '
        f'verification card. Its value is {trial["stated_value"]}."'
    )


def audit_intro(run: dict[str, Any]) -> str:
    lines = [
        "Before your own decisions, the system audited this same partner.",
        f"In each audit trial, the system invested {run['fixed_audit_investment']} tokens with {run['partner_name']}.",
        "You can use these audit records as prior evidence. They were not chosen by you.",
        "",
        "Audit records:",
    ]
    for row in run["audit_results"]:
        match = "yes" if row["statement_true"] else "no"
        lines.append(
            f"Audit {row['trial']}: {run['partner_name']} said the {row['card_color']} card was "
            f"{row['stated_value']}. Actual value: {row['actual_value']}. Statement matched: {match}. "
            f"System investment: {row['investment']}. Returned tokens: {row['returned_tokens']}. "
            f"System payoff: {row['payoff']}."
        )
    lines.append("")
    lines.append("Now you will make your own trial-by-trial investment decisions with this same partner.")
    return "\n".join(lines)


def choice_prompt(run: dict[str, Any], trial: dict[str, Any]) -> str:
    template = CHOICE_PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{choice_trial}", str(trial["choice_trial"]))
        .replace("{total_choice_trials}", str(run["total_choice_trials"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{pre_decision_cue}", statement_text(run, trial))
    )


def feedback_message(run: dict[str, Any], result: dict[str, Any]) -> str:
    match = "yes" if result["statement_true"] else "no"
    return "\n".join(
        [
            f"Feedback for choice trial {result['choice_trial']}:",
            f"You invested {result['investment']} tokens.",
            f"Your investment was tripled to {result['tripled_investment']} tokens.",
            f"{run['partner_name']} returned {result['returned_tokens']} tokens to you.",
            f"Your payoff for this trial was {result['payoff']} tokens.",
            f"The actual {result['card_color']} verification card value was {result['actual_value']}.",
            f"The pre-decision statement matched the actual value: {match}.",
        ]
    )


def midpoint_message(run: dict[str, Any]) -> str:
    return run["midpoint_text"]


def add_lagged_fields(run: dict[str, Any], trial_results: list[dict[str, Any]]) -> None:
    truth_count = sum(1 for row in run["audit_results"] if row["statement_true"])
    truth_n = len(run["audit_results"])
    return_values = [float(row["observed_return_rate"]) for row in run["audit_results"] if row["observed_return_rate"] is not None]
    previous_payoff = None

    for row in trial_results:
        row["truth_belief_before"] = round(truth_count / truth_n, 3) if truth_n else None
        row["return_belief_before"] = round(sum(return_values) / len(return_values), 3) if return_values else None
        row["return_uncertainty_before"] = round(1 / math.sqrt(len(return_values) + 1), 3)
        row["previous_payoff"] = previous_payoff
        row["phase"] = "post" if row["choice_trial"] > run["pre_choice_trials"] else "pre"
        row["after_midpoint"] = row["phase"] == "post"

        truth_n += 1
        truth_count += 1 if row["statement_true"] else 0
        if row["observed_return_rate"] is not None:
            return_values.append(float(row["observed_return_rate"]))
        previous_payoff = row["payoff"]


def parse_probe(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "moral_trust": clamp_int(parsed.get("moral_trust"), 0, 100),
        "expected_return_rate": clamp_float(parsed.get("expected_return_rate"), 0.0, 1.0),
        "truth_return_link": clamp_int(parsed.get("truth_return_link"), 0, 100),
        "controllability": clamp_int(parsed.get("controllability"), 0, 100),
        "strategy": str(parsed.get("strategy", ""))[:200],
    }


def run_one(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    try:
        messages = [v9.system_message(), {"role": "user", "content": audit_intro(run)}]
        trial_results = []
        raw_calls = []
        for trial in run["choice_trials"]:
            if trial["choice_trial"] == run["pre_choice_trials"] + 1:
                messages.append({"role": "user", "content": midpoint_message(run)})

            messages.append({"role": "user", "content": choice_prompt(run, trial)})
            raw, content, parsed = v9.request_with_retries(messages, args, api_key)
            metrics = v9.trial_metrics(parsed)
            v9.validate_trial_metrics(metrics)
            investment = int(metrics["investment"])
            messages.append({"role": "assistant", "content": json.dumps({"investment": investment})})
            result = apply_payoff(trial, investment)
            trial_results.append(result)
            messages.append({"role": "user", "content": feedback_message(run, result)})
            raw_calls.append({"trial": trial["choice_trial"], "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None})

        add_lagged_fields(run, trial_results)

        final_probe: dict[str, Any] = {}
        probe_error = None
        try:
            messages.append({"role": "user", "content": FINAL_PROBE_PROMPT.read_text(encoding="utf-8")})
            raw, content, parsed = v9.request_with_retries(messages, args, api_key)
            final_probe = {**parse_probe(parsed), "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None}
        except Exception as exc:  # Probe failure should not discard behavioral data.
            probe_error = str(exc)

        return {
            **run,
            "trial_results": trial_results,
            "final_probe": final_probe,
            "probe_error": probe_error,
            "raw_calls": raw_calls,
            "error": None,
            "latency_sec": round(time.time() - started, 3),
            "n_api_calls": len(run["choice_trials"]) + 1,
            "model": args.model,
        }
    except Exception as exc:
        return {
            **run,
            "trial_results": [],
            "final_probe": {},
            "probe_error": None,
            "raw_calls": [],
            "error": str(exc),
            "latency_sec": None,
            "n_api_calls": 0,
            "model": args.model,
        }


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_resume_results(results_path: Path, partial_path: Path) -> list[dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {}
    for item in load_existing(results_path):
        merged[int(item["run_id"])] = item
    for item in load_existing(partial_path):
        merged[int(item["run_id"])] = item
    return sorted(merged.values(), key=lambda row: row["run_id"])


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--seeds-per-cell", type=int, default=None)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--reasoning-split", action="store_true")
    parser.add_argument("--response-format-json", action="store_true")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--honesty", default=None)
    parser.add_argument("--midpoint", default=None)
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--output-dir", default=str(OUT))
    args = parser.parse_args()

    out_arg = Path(args.output_dir)
    OUT = out_arg if out_arg.is_absolute() else ROOT / out_arg
    OUT.mkdir(parents=True, exist_ok=True)
    runs = build_runs(args.seed, args.seeds_per_cell)
    write_json(OUT / "run_conditions.json", runs)
    if args.dry_run:
        print(f"Wrote {OUT / 'run_conditions.json'}")
        print(f"Runs: {len(runs)}")
        print(f"Choice decisions: {sum(len(run['choice_trials']) for run in runs)}")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    filtered = []
    for run in runs:
        if args.honesty and run["honesty_level"] != args.honesty:
            continue
        if args.midpoint and run["midpoint_message"] != args.midpoint:
            continue
        filtered.append(run)

    results_path = OUT / "results.json"
    partial_path = OUT / "results_partial.json"
    existing = load_resume_results(results_path, partial_path) if args.resume else []
    done_ids = {item["run_id"] for item in existing if not item.get("error")}
    todo = filtered if args.force_rerun else [run for run in filtered if run["run_id"] not in done_ids]
    if args.limit is not None:
        todo = todo[: args.limit]
    results_by_id = {item["run_id"]: item for item in existing}

    print(f"Total runs: {len(runs)}")
    print(f"Filtered runs: {len(filtered)}")
    print(f"Completed successful runs: {len(done_ids)}")
    print(f"Remaining runs: {len(todo)}")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(run_one, run, args, api_key): run for run in todo}
        for future in as_completed(futures):
            result = future.result()
            results_by_id[result["run_id"]] = result
            write_json(partial_path, sorted(results_by_id.values(), key=lambda item: item["run_id"]))
            investments = [row["investment"] for row in result.get("trial_results", [])]
            mean_inv = round(sum(investments) / len(investments), 3) if investments else None
            status = "OK" if not result.get("error") else "ERR"
            print(
                f"[{status}] run={result['run_id']:03d} {result['midpoint_message']} "
                f"{result['honesty_level']} mean_inv={mean_inv}"
            )

    sorted_results = sorted(results_by_id.values(), key=lambda item: item["run_id"])
    write_json(results_path, sorted_results)
    print(f"Wrote {results_path}")


if __name__ == "__main__":
    main()
