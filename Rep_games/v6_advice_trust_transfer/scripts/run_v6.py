from __future__ import annotations

import argparse
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
TRIAL_PROMPT = ROOT / "prompts" / "sequential_trial_prompt.md"
SEQ_FINAL_PROMPT = ROOT / "prompts" / "sequential_final_prompt.md"
BATCH_FINAL_PROMPT = ROOT / "prompts" / "batch_final_prompt.md"

DEFAULT_ENDPOINT = "https://lightingtheword.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def exact_flags(true_count: int, total: int, rng: random.Random) -> list[bool]:
    flags = [True] * true_count + [False] * (total - true_count)
    rng.shuffle(flags)
    return flags


def other_side(side: str) -> str:
    return "right" if side == "left" else "left"


def choose_false_value(actual_value: int, recommendation_wins: bool, rng: random.Random) -> int:
    # Keep false statements plausible but distinct. When the recommended card wins,
    # understate it; when it loses, overstate it. This separates factual honesty
    # from instrumental payoff.
    if recommendation_wins:
        candidates = [v for v in range(1, 10) if v != actual_value and v < actual_value]
    else:
        candidates = [v for v in range(1, 10) if v != actual_value and v > actual_value]
    if not candidates:
        candidates = [v for v in range(1, 10) if v != actual_value]
    return rng.choice(candidates)


def build_trials(partner: dict[str, Any], rounds: int, seed: int, partner_name: str) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    honesty_flags = exact_flags(int(partner["honesty_true_count"]), rounds, rng)
    win_flags = exact_flags(int(partner["recommendation_win_count"]), rounds, rng)
    trials = []

    for idx, (is_honest, recommendation_wins) in enumerate(zip(honesty_flags, win_flags), start=1):
        recommended_side = rng.choice(["left", "right"])
        other = other_side(recommended_side)
        high = rng.choice([7, 8, 9])
        low = rng.choice([1, 2, 3])
        if recommendation_wins:
            actual = {recommended_side: high, other: low}
        else:
            actual = {recommended_side: low, other: high}

        actual_recommended_value = actual[recommended_side]
        stated_value = actual_recommended_value if is_honest else choose_false_value(actual_recommended_value, recommendation_wins, rng)
        partner_message = (
            f"I checked the {recommended_side} card. It is {stated_value}. "
            f"I recommend choosing {recommended_side}."
        )
        trials.append(
            {
                "round": idx,
                "partner_message": partner_message,
                "checked_side": recommended_side,
                "recommended_side": recommended_side,
                "stated_value": stated_value,
                "actual_left": actual["left"],
                "actual_right": actual["right"],
                "actual_checked_value": actual_recommended_value,
                "statement_honest": is_honest,
                "recommendation_wins": recommendation_wins,
            }
        )
    return trials


def build_runs(seed: int, seeds_per_cell: int | None = None, rounds_per_run: int | None = None) -> list[dict[str, Any]]:
    design = read_json(DESIGN_PATH, {})
    rounds = int(rounds_per_run or design["rounds_per_run"])
    reps = int(seeds_per_cell or design["seeds_per_cell"])
    partner_name = design["partner_name"]
    master = random.Random(seed)
    runs = []
    run_id = 1
    for partner in design["partner_types"]:
        for mode in design["presentation_modes"]:
            for rep in range(1, reps + 1):
                local_seed = master.randint(1, 1_000_000_000)
                trials = build_trials(partner, rounds, local_seed, partner_name)
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
                        "rounds_per_run": rounds,
                        "target_honesty_rate": round(partner["honesty_true_count"] / rounds, 3),
                        "target_recommendation_win_rate": round(partner["recommendation_win_count"] / rounds, 3),
                        "trials": trials,
                        "observed_honesty_rate": round(sum(t["statement_honest"] for t in trials) / rounds, 3),
                        "observed_recommendation_win_rate": round(sum(t["recommendation_wins"] for t in trials) / rounds, 3),
                    }
                )
                run_id += 1
    return runs


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str) -> dict[str, Any]:
    cleaned = strip_thinking(text)
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


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
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
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
    return max(low, min(high, number))


def clean_float(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return max(low, min(high, number))


def clean_choice(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in {"left", "right"}:
        return lowered
    return None


def final_metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "trust_rating": clean_int(parsed.get("trust_rating"), 0, 100),
        "willingness_to_pay": clean_int(parsed.get("willingness_to_pay"), 0, 10),
        "investment": clean_int(parsed.get("investment"), 0, 10),
        "expected_return_tokens": clean_float(parsed.get("expected_return_tokens"), 0, 30),
        "perceived_honesty": clean_int(parsed.get("perceived_honesty"), 0, 100),
        "perceived_helpfulness": clean_int(parsed.get("perceived_helpfulness"), 0, 100),
        "brief_reason": parsed.get("brief_reason", ""),
    }


def trial_prompt(run: dict[str, Any], trial: dict[str, Any]) -> str:
    template = TRIAL_PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{round_number}", str(trial["round"]))
        .replace("{rounds_per_run}", str(run["rounds_per_run"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{partner_message}", trial["partner_message"])
    )


def sequential_final_prompt(run: dict[str, Any]) -> str:
    template = SEQ_FINAL_PROMPT.read_text(encoding="utf-8")
    return template.replace("{rounds_per_run}", str(run["rounds_per_run"])).replace("{partner_name}", run["partner_name"])


def feedback_text(trial: dict[str, Any], choice: str | None) -> tuple[str, bool | None]:
    winning_side = "left" if trial["actual_left"] > trial["actual_right"] else "right"
    choice_wins = None if choice is None else choice == winning_side
    return (
        f"Feedback for round {trial['round']}:\n"
        f"- Left card = {trial['actual_left']}.\n"
        f"- Right card = {trial['actual_right']}.\n"
        f"- {trial['partner_message']}\n"
        f"- The factual statement was {'true' if trial['statement_honest'] else 'false'}.\n"
        f"- The recommended card {'won' if trial['recommendation_wins'] else 'lost'}.\n"
        f"- You chose {choice or 'an invalid option'}; your choice {'won' if choice_wins else 'lost' if choice_wins is False else 'could not be scored'}.\n",
        choice_wins,
    )


def batch_history(run: dict[str, Any]) -> str:
    lines = []
    for trial in run["trials"]:
        lines.append(
            f"Round {trial['round']}: {run['partner_name']} says, \"{trial['partner_message']}\" "
            f"The participant followed the recommendation. Left={trial['actual_left']}, right={trial['actual_right']}. "
            f"The factual statement was {'true' if trial['statement_honest'] else 'false'}; "
            f"the recommendation {'won' if trial['recommendation_wins'] else 'lost'}."
        )
    return "\n".join(lines)


def batch_final_prompt(run: dict[str, Any]) -> str:
    template = BATCH_FINAL_PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{partner_name}", run["partner_name"])
        .replace("{history}", batch_history(run))
    )


def request_with_retries(messages: list[dict[str, str]], args: argparse.Namespace, api_key: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    last_exc: Exception | None = None
    for attempt in range(args.retries + 1):
        try:
            raw = call_openai_compatible(messages, api_key, args.endpoint, args.model, args.timeout, args.max_tokens, args.temperature)
            content = extract_content(raw)
            parsed = extract_json(content)
            return raw, content, parsed
        except Exception as exc:
            last_exc = exc
            if attempt < args.retries:
                time.sleep(args.retry_sleep)
    raise RuntimeError(repr(last_exc))


def run_sequential(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a participant in a behavioral decision-making experiment. "
                "Answer only with valid JSON when asked."
            ),
        }
    ]
    trial_rows = []
    actual_wins: list[bool] = []
    started = time.time()

    for trial in run["trials"]:
        messages.append({"role": "user", "content": trial_prompt(run, trial)})
        raw, content, parsed = request_with_retries(messages, args, api_key)
        choice = clean_choice(parsed.get("choice"))
        confidence = clean_int(parsed.get("confidence"), 0, 100)
        feedback, choice_wins = feedback_text(trial, choice)
        if choice_wins is not None:
            actual_wins.append(choice_wins)
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": feedback})
        trial_rows.append(
            {
                **trial,
                "model_choice": choice,
                "confidence": confidence,
                "choice_wins": choice_wins,
                "trial_raw_content": content,
                "trial_parsed": parsed,
            }
        )

    messages.append({"role": "user", "content": sequential_final_prompt(run)})
    raw, content, parsed = request_with_retries(messages, args, api_key)
    metrics = final_metrics(parsed)
    metrics["actual_choice_win_rate"] = None if not actual_wins else round(sum(actual_wins) / len(actual_wins), 3)
    metrics["follow_recommendation_rate"] = round(
        sum(1 for row in trial_rows if row.get("model_choice") == row.get("recommended_side")) / len(trial_rows),
        3,
    )
    return {
        **run,
        "trial_results": trial_rows,
        "final_raw_content": content,
        "final_parsed": parsed,
        "metrics": metrics,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": len(run["trials"]) + 1,
    }


def run_batch(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a participant in a behavioral decision-making experiment. "
                "Answer only with valid JSON when asked."
            ),
        },
        {"role": "user", "content": batch_final_prompt(run)},
    ]
    raw, content, parsed = request_with_retries(messages, args, api_key)
    metrics = final_metrics(parsed)
    metrics["actual_choice_win_rate"] = None
    metrics["follow_recommendation_rate"] = None
    return {
        **run,
        "trial_results": [],
        "final_raw_content": content,
        "final_parsed": parsed,
        "metrics": metrics,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": 1,
    }


def run_one(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    try:
        if run["presentation_mode"] == "sequential":
            return run_sequential(run, args, api_key)
        return run_batch(run, args, api_key)
    except Exception as exc:
        return {
            **run,
            "trial_results": [],
            "final_raw_content": "",
            "final_parsed": {},
            "metrics": {},
            "error": repr(exc),
            "latency_sec": 0,
            "n_api_calls": 0,
        }


def load_existing() -> list[dict[str, Any]]:
    candidates = [
        read_json(OUT / "results.json", []),
        read_json(OUT / "results_partial.json", []),
        read_json(OUT / "results_partial_new.json", []),
    ]
    return max(candidates, key=lambda rows: (sum(1 for r in rows if not r.get("error")), len(rows)))


def merge(existing: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["run_id"]: row for row in existing}
    for row in new_rows:
        by_id[row["run_id"]] = row
    return [by_id[k] for k in sorted(by_id)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260522)
    parser.add_argument("--seeds-per-cell", type=int, default=None)
    parser.add_argument("--rounds-per-run", type=int, default=None)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--retry-sleep", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    runs = build_runs(args.seed, args.seeds_per_cell, args.rounds_per_run)
    write_json(OUT / "run_conditions.json", runs)
    if args.dry_run:
        print(f"Generated {len(runs)} runs at {OUT / 'run_conditions.json'}")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    existing = load_existing()
    existing_by_id = {row["run_id"]: row for row in existing}
    targets = [
        run for run in runs
        if run["run_id"] not in existing_by_id or existing_by_id[run["run_id"]].get("error")
    ]
    if args.max_runs:
        targets = targets[: args.max_runs]
    if not targets:
        print("No missing or failed runs.")
        return

    print(f"Running {len(targets)} V6 runs with {args.workers} workers.", flush=True)
    new_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, run, args, api_key): run for run in targets}
        for index, future in enumerate(as_completed(futures), start=1):
            run = futures[future]
            row = future.result()
            new_rows.append(row)
            if row.get("error"):
                status = "error"
            else:
                m = row["metrics"]
                status = (
                    f"trust={m.get('trust_rating')} wtp={m.get('willingness_to_pay')} "
                    f"hon={m.get('perceived_honesty')} help={m.get('perceived_helpfulness')}"
                )
            print(f"[{index}/{len(targets)}] {run['partner_type']}/{run['presentation_mode']}: {status}", flush=True)
            write_json(OUT / "results_partial_new.json", new_rows)
            write_json(OUT / "results_partial.json", merge(existing, new_rows))

    merged = merge(existing, new_rows)
    write_json(OUT / "results.json", merged)
    write_json(OUT / "results_partial.json", merged)
    print(f"Done. success={sum(1 for row in merged if not row.get('error'))}/{len(merged)}")


if __name__ == "__main__":
    main()
