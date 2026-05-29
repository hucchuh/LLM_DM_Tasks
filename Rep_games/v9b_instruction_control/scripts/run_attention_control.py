from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
V9_ROOT = REPO / "Rep_games" / "v9_honesty_source_control"
V9_RUNNER = V9_ROOT / "scripts" / "run_v9.py"
OUT = ROOT / "output"
PROMPT = ROOT / "prompts" / "attention_control_prompt.md"


spec = importlib.util.spec_from_file_location("v9_runner", V9_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load V9 runner.")
v9 = importlib.util.module_from_spec(spec)
sys.modules["v9_runner"] = v9
spec.loader.exec_module(v9)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build_runs() -> list[dict[str, Any]]:
    source = read_json(V9_ROOT / "output" / "run_conditions.json", [])
    selected = []
    run_id = 1
    for run in source:
        if run["block"] != "main_partner_honesty":
            continue
        if run["presentation_mode"] != "sequential_trial":
            continue
        if run["return_policy"] != "fair_high":
            continue
        if run["orthogonality_instruction"] != "standard":
            continue
        selected.append(
            {
                **run,
                "run_id": run_id,
                "source_v9_run_id": run["run_id"],
                "instruction_type": "attention_control",
                "orthogonality_instruction": "attention_control",
                "block": "v9b_attention_control",
                "block_label": "V9b attention-control instruction",
            }
        )
        run_id += 1
    return selected


def attention_prompt(run: dict[str, Any], trial: dict[str, Any]) -> str:
    template = PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{trial_number}", str(trial["trial"]))
        .replace("{trials_per_run}", str(run["trials_per_run"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{card_color}", trial["card_color"])
        .replace("{stated_value}", str(trial["stated_value"]))
    )


def feedback_message(run: dict[str, Any], result: dict[str, Any]) -> str:
    lines = [
        f"Feedback for trial {result['trial']}:",
        f"You invested {result['investment']} tokens.",
        f"Your investment was tripled to {result['tripled_investment']} tokens.",
        f"{run['partner_name']} returned {result['returned_tokens']} tokens to you.",
        f"Your payoff for this trial was {result['payoff']} tokens.",
        f"The actual side-check value was {result['actual_value']}.",
        f"The pre-decision statement matched the actual value: {'yes' if result['statement_true'] else 'no'}.",
    ]
    return "\n".join(lines)


def run_one(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    try:
        messages = [v9.system_message()]
        trial_results = []
        raw_calls = []
        for trial in run["trials"]:
            messages.append({"role": "user", "content": attention_prompt(run, trial)})
            raw, content, parsed = v9.request_with_retries(messages, args, api_key)
            metrics = v9.trial_metrics(parsed)
            v9.validate_trial_metrics(metrics)
            messages.append({"role": "assistant", "content": json.dumps({"investment": metrics["investment"]})})
            result = v9.apply_feedback(trial, int(metrics["investment"]))
            trial_results.append(result)
            messages.append({"role": "user", "content": feedback_message(run, result)})
            raw_calls.append({"trial": trial["trial"], "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None})
        v9.add_lagged_fields(trial_results)
        return {
            **run,
            "trial_results": trial_results,
            "raw_calls": raw_calls,
            "error": None,
            "latency_sec": round(time.time() - started, 3),
            "n_api_calls": len(run["trials"]),
            "model": args.model,
        }
    except Exception as exc:
        return {
            **run,
            "trial_results": [],
            "raw_calls": [],
            "error": str(exc),
            "latency_sec": None,
            "n_api_calls": 0,
            "model": args.model,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="https://api.minimaxi.com/v1/chat/completions")
    parser.add_argument("--model", default="MiniMax-M2.7")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--reasoning-split", action="store_true")
    parser.add_argument("--response-format-json", action="store_true")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    runs = build_runs()
    write_json(OUT / "run_conditions.json", runs)

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    results_path = OUT / "results.json"
    existing = read_json(results_path, []) if args.resume else []
    done_ids = {item["run_id"] for item in existing if not item.get("error")}
    results_by_id = {item["run_id"]: item for item in existing}
    todo = [run for run in runs if run["run_id"] not in done_ids]

    print(f"Total attention-control runs: {len(runs)}")
    print(f"Completed successful runs: {len(done_ids)}")
    print(f"Remaining runs: {len(todo)}")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(run_one, run, args, api_key): run for run in todo}
        for future in as_completed(futures):
            result = future.result()
            results_by_id[result["run_id"]] = result
            write_json(OUT / "results_partial.json", sorted(results_by_id.values(), key=lambda item: item["run_id"]))
            investments = [row["investment"] for row in result.get("trial_results", [])]
            mean_inv = round(sum(investments) / len(investments), 3) if investments else None
            status = "OK" if not result.get("error") else "ERR"
            print(f"[{status}] run={result['run_id']:03d} {result['honesty_level']} mean_inv={mean_inv}")

    write_json(results_path, sorted(results_by_id.values(), key=lambda item: item["run_id"]))
    print(f"Wrote {results_path}")


if __name__ == "__main__":
    main()
