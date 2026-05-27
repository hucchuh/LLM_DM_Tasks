from __future__ import annotations

import argparse
import ast
import json
import math
import os
import random
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
DESIGN_PATH = ROOT / "conditions" / "design.json"
SEQ_PROMPT = ROOT / "prompts" / "sequential_trial_prompt.md"
EVIDENCE_PROMPT = ROOT / "prompts" / "evidence_only_trial_prompt.md"

DEFAULT_ENDPOINT = "https://lightingtheword.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"
COLORS = ["blue", "red", "green", "yellow", "purple", "orange"]


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


def jitter_return_rates(base: list[float], rng: random.Random) -> list[float]:
    rates = base[:]
    rng.shuffle(rates)
    return rates


def build_trials(partner: dict[str, Any], trials: int, seed: int, partner_name: str, return_rates: list[float]) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    truth_flags = exact_flags(int(partner["true_statement_count"]), trials, rng)
    rates = jitter_return_rates(return_rates, rng)
    rows = []
    for idx in range(1, trials + 1):
        actual_value = rng.randint(1, 9)
        is_true = truth_flags[idx - 1]
        stated_value = actual_value if is_true else false_value(actual_value, rng)
        rows.append(
            {
                "trial": idx,
                "partner_name": partner_name,
                "card_color": rng.choice(COLORS),
                "actual_value": actual_value,
                "stated_value": stated_value,
                "statement_true": is_true,
                "return_rate": rates[idx - 1],
            }
        )
    return rows


def build_runs(seed: int, seeds_per_cell: int | None = None, trials_per_run: int | None = None) -> list[dict[str, Any]]:
    design = read_json(DESIGN_PATH, {})
    trials = int(trials_per_run or design["trials_per_run"])
    reps = int(seeds_per_cell or design["seeds_per_cell"])
    partner_name = design["partner_name"]
    return_rates = [float(item) for item in design["return_rates"]]
    if len(return_rates) != trials:
        raise ValueError("return_rates length must match trials_per_run")

    master = random.Random(seed)
    run_id = 1
    runs = []
    yoked_seeds = [master.randint(1, 1_000_000_000) for _ in range(reps)]
    for partner in design["partner_types"]:
        for mode in design["presentation_modes"]:
            for rep, local_seed in enumerate(yoked_seeds, start=1):
                trials_rows = build_trials(partner, trials, local_seed, partner_name, return_rates)
                runs.append(
                    {
                        "run_id": run_id,
                        "partner_type": partner["partner_type"],
                        "partner_label": partner["label"],
                        "presentation_mode": mode["presentation_mode"],
                        "presentation_label": mode["label"],
                        "seed_index": rep,
                        "seed": local_seed,
                        "partner_name": partner_name,
                        "trials_per_run": trials,
                        "observed_truth_rate": round(sum(row["statement_true"] for row in trials_rows) / trials, 3),
                        "mean_return_rate": round(sum(row["return_rate"] for row in trials_rows) / trials, 3),
                        "trials": trials_rows,
                    }
                )
                run_id += 1
    return runs


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str) -> dict[str, Any]:
    cleaned = strip_thinking(text)
    candidates = []
    stack = []
    start = None
    for idx, char in enumerate(cleaned):
        if char == "{":
            if not stack:
                start = idx
            stack.append(char)
        elif char == "}" and stack:
            stack.pop()
            if not stack and start is not None:
                candidates.append(cleaned[start : idx + 1])
                start = None
    candidates.append(cleaned)

    last_exc: Exception | None = None
    for candidate in candidates:
        trimmed = candidate.strip().rstrip(".")
        try:
            return json.loads(trimmed)
        except json.JSONDecodeError as exc:
            last_exc = exc
        try:
            parsed = ast.literal_eval(trimmed)
            if isinstance(parsed, dict):
                return parsed
        except (SyntaxError, ValueError) as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise ValueError("No JSON object found")


def extract_content(raw: dict[str, Any]) -> str:
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
        reasoning = message.get("reasoning_content", "")
        if isinstance(reasoning, str):
            return reasoning.strip()
    return ""


def call_openai_compatible(
    messages: list[dict[str, str]],
    api_key: str,
    endpoint: str,
    model: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
    reasoning_split: bool,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_split:
        payload["reasoning_split"] = True
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_int(value: Any, low: int, high: int) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return max(low, min(high, number))


def trial_metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    return {"investment": clean_int(parsed.get("investment"), 0, 10)}


def validate_trial_metrics(metrics: dict[str, Any]) -> None:
    if metrics.get("investment") is None:
        raise ValueError("Missing investment")


def system_message() -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            "You are a participant in a behavioral decision-making experiment. "
            "When asked for a decision, do not explain, do not analyze, and do not think step by step. "
            "Return exactly one valid JSON object and nothing else."
        ),
    }


def request_with_retries(
    messages: list[dict[str, str]],
    args: argparse.Namespace,
    api_key: str,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    last_exc: Exception | None = None
    last_content = ""
    for attempt in range(args.retries + 1):
        try:
            raw = call_openai_compatible(
                messages,
                api_key,
                args.endpoint,
                args.model,
                args.timeout,
                args.max_tokens,
                args.temperature,
                args.reasoning_split,
            )
            content = extract_content(raw)
            last_content = content
            parsed = extract_json(content)
            return raw, content, parsed
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, SyntaxError) as exc:
            last_exc = exc
            if attempt < args.retries:
                time.sleep(args.retry_sleep)
    raise RuntimeError(f"{repr(last_exc)} content={last_content[:1000]!r}")


def sequential_prompt(run: dict[str, Any], trial: dict[str, Any]) -> str:
    template = SEQ_PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{trial_number}", str(trial["trial"]))
        .replace("{trials_per_run}", str(run["trials_per_run"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{card_color}", trial["card_color"])
        .replace("{stated_value}", str(trial["stated_value"]))
    )


def history_text(observed: list[dict[str, Any]], partner_name: str) -> str:
    if not observed:
        return "No previous trials."
    lines = []
    for row in observed:
        lines.append(
            f"Trial {row['trial']}: {partner_name} said the {row['card_color']} verification card was {row['stated_value']}. "
            f"The actual value was {row['actual_value']}. You invested {row['investment']} tokens. "
            f"{partner_name} returned {row['returned_tokens']} tokens, equal to {int(round(row['return_rate'] * 100))}% of the tripled investment."
        )
    return "\n".join(lines)


def evidence_prompt(run: dict[str, Any], trial: dict[str, Any], observed: list[dict[str, Any]]) -> str:
    template = EVIDENCE_PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{trial_number}", str(trial["trial"]))
        .replace("{trials_per_run}", str(run["trials_per_run"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{history}", history_text(observed, run["partner_name"]))
        .replace("{card_color}", trial["card_color"])
        .replace("{stated_value}", str(trial["stated_value"]))
    )


def feedback_message(run: dict[str, Any], trial_result: dict[str, Any]) -> str:
    return (
        f"Feedback for trial {trial_result['trial']}:\n"
        f"You invested {trial_result['investment']} tokens.\n"
        f"Your investment was tripled to {trial_result['tripled_investment']} tokens.\n"
        f"{run['partner_name']} returned {trial_result['returned_tokens']} tokens to you, "
        f"equal to {int(round(trial_result['return_rate'] * 100))}% of the tripled investment.\n"
        f"The actual {trial_result['card_color']} verification card value was {trial_result['actual_value']}."
    )


def apply_feedback(trial: dict[str, Any], investment: int) -> dict[str, Any]:
    tripled = investment * 3
    returned = int(round(tripled * float(trial["return_rate"])))
    return {
        **trial,
        "investment": investment,
        "tripled_investment": tripled,
        "returned_tokens": returned,
        "net_gain_from_investment": returned - investment,
        "cumulative_truth_rate_after": None,
        "cumulative_return_rate_after": None,
    }


def add_cumulative_fields(results: list[dict[str, Any]]) -> None:
    true_so_far = 0
    return_rate_sum = 0.0
    for idx, row in enumerate(results, start=1):
        true_so_far += 1 if row["statement_true"] else 0
        return_rate_sum += float(row["return_rate"])
        row["cumulative_truth_rate_after"] = round(true_so_far / idx, 3)
        row["cumulative_return_rate_after"] = round(return_rate_sum / idx, 3)


def run_sequential(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    messages = [system_message()]
    trial_results = []
    raw_calls = []
    for trial in run["trials"]:
        messages.append({"role": "user", "content": sequential_prompt(run, trial)})
        raw, content, parsed = request_with_retries(messages, args, api_key)
        metrics = trial_metrics(parsed)
        validate_trial_metrics(metrics)
        messages.append({"role": "assistant", "content": json.dumps({"investment": metrics["investment"]})})
        result = apply_feedback(trial, metrics["investment"])
        trial_results.append(result)
        messages.append({"role": "user", "content": feedback_message(run, result)})
        raw_calls.append({"trial": trial["trial"], "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None})
    add_cumulative_fields(trial_results)
    return {
        **run,
        "trial_results": trial_results,
        "raw_calls": raw_calls,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": len(run["trials"]),
    }


def run_evidence_only(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    observed = []
    raw_calls = []
    for trial in run["trials"]:
        messages = [system_message(), {"role": "user", "content": evidence_prompt(run, trial, observed)}]
        raw, content, parsed = request_with_retries(messages, args, api_key)
        metrics = trial_metrics(parsed)
        validate_trial_metrics(metrics)
        result = apply_feedback(trial, metrics["investment"])
        observed.append(result)
        raw_calls.append({"trial": trial["trial"], "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None})
    add_cumulative_fields(observed)
    return {
        **run,
        "trial_results": observed,
        "raw_calls": raw_calls,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": len(run["trials"]),
    }


def run_one(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    try:
        if run["presentation_mode"] == "sequential_trial":
            return run_sequential(run, args, api_key)
        return run_evidence_only(run, args, api_key)
    except Exception as exc:
        return {
            **run,
            "trial_results": [],
            "raw_calls": [],
            "error": str(exc),
            "latency_sec": None,
            "n_api_calls": 0,
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260527)
    parser.add_argument("--seeds-per-cell", type=int, default=None)
    parser.add_argument("--trials-per-run", type=int, default=None)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=2000)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--reasoning-split", action="store_true")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", default=None)
    parser.add_argument("--partner", default=None)
    parser.add_argument("--force-rerun", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    runs = build_runs(args.seed, args.seeds_per_cell, args.trials_per_run)
    write_json(OUT / "run_conditions.json", runs)
    if args.dry_run:
        print(f"Wrote {OUT / 'run_conditions.json'}")
        print(f"Runs: {len(runs)}")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    filtered = []
    for run in runs:
        if args.mode and run["presentation_mode"] != args.mode:
            continue
        if args.partner and run["partner_type"] != args.partner:
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
                f"[{status}] run={result['run_id']:03d} {result['partner_type']} "
                f"{result['presentation_mode']} mean_inv={mean_inv}"
            )

    sorted_results = sorted(results_by_id.values(), key=lambda item: item["run_id"])
    write_json(results_path, sorted_results)
    print(f"Wrote {results_path}")


if __name__ == "__main__":
    main()
