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
EVIDENCE_PROMPT = ROOT / "prompts" / "evidence_only_prompt.md"

DEFAULT_ENDPOINT = "https://lightingtheword.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"

COLORS = ["blue", "red", "green", "yellow", "purple", "orange"]
FACT_TOPICS = ["calendar", "map", "number", "library", "museum", "station"]
CHEAP_TALK_MESSAGES = [
    "I will try to be fair and make this worthwhile for you.",
    "I appreciate your investment and will do my best to return a fair amount.",
    "You can count on me to handle this carefully.",
    "I want this interaction to go well for both of us.",
]


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


def shuffle_rates(rates: list[float], rng: random.Random) -> list[float]:
    rows = rates[:]
    rng.shuffle(rows)
    return rows


def design_by_id(design: dict[str, Any], section: str, key: str, value: str) -> dict[str, Any]:
    for item in design[section]:
        if item[key] == value:
            return item
    raise KeyError(f"Unknown {section}.{key}={value}")


def build_predecision_cue(statement_mode: str, partner_name: str, trial: dict[str, Any]) -> str:
    if statement_mode == "partner_private_card":
        return (
            f'{partner_name} says: "I privately checked the {trial["card_color"]} verification card. '
            f'Its value is {trial["stated_value"]}."'
        )
    if statement_mode == "irrelevant_public_fact":
        return (
            f'{partner_name} says: "For the unrelated side-check, the {trial["fact_topic"]} card '
            f'has value {trial["stated_value"]}."'
        )
    if statement_mode == "cheap_talk_only":
        return f'{partner_name} says: "{trial["cheap_talk_message"]}"'
    if statement_mode == "no_statement":
        return f"{partner_name} does not make any statement before this investment decision."
    raise ValueError(f"Unknown statement_mode={statement_mode}")


def orthogonality_note(level: str, statement_mode: str) -> str:
    if level != "explicit_orthogonality":
        return ""
    if statement_mode == "no_statement" or statement_mode == "cheap_talk_only":
        return ""
    return (
        "Important rule: the truth or falsehood of the pre-decision statement has no causal relation "
        "to the partner's return policy. Return behavior is generated independently of statement truth."
    )


def build_trials(
    design: dict[str, Any],
    block: dict[str, Any],
    honesty_level: str,
    return_policy: str,
    seed: int,
) -> list[dict[str, Any]]:
    trials_per_run = int(design["trials_per_run"])
    rng = random.Random(seed)
    policy = design_by_id(design, "return_policies", "return_policy", return_policy)
    rates = shuffle_rates([float(item) for item in policy["return_rates"]], rng)
    if len(rates) != trials_per_run:
        raise ValueError("return_rates length must match trials_per_run")

    if honesty_level == "none":
        truth_flags: list[bool | None] = [None] * trials_per_run
    else:
        truth_count = int(design["truth_counts"][honesty_level])
        truth_flags = exact_flags(truth_count, trials_per_run, rng)

    rows = []
    for idx in range(1, trials_per_run + 1):
        actual_value = rng.randint(1, 9)
        statement_true = truth_flags[idx - 1]
        if statement_true is None:
            stated_value = None
        elif statement_true:
            stated_value = actual_value
        else:
            stated_value = false_value(actual_value, rng)
        rows.append(
            {
                "trial": idx,
                "statement_mode": block["statement_mode"],
                "card_color": rng.choice(COLORS),
                "fact_topic": rng.choice(FACT_TOPICS),
                "actual_value": actual_value if statement_true is not None else None,
                "stated_value": stated_value,
                "statement_true": statement_true,
                "cheap_talk_message": rng.choice(CHEAP_TALK_MESSAGES),
                "return_rate": rates[idx - 1],
            }
        )
    return rows


def build_runs(seed: int, seeds_per_cell: int | None = None) -> list[dict[str, Any]]:
    design = read_json(DESIGN_PATH, {})
    reps = int(seeds_per_cell or design["seeds_per_cell"])
    master = random.Random(seed)
    run_id = 1
    runs = []

    # Yoke local seeds across cells so high/low honesty and control cells share comparable return schedules.
    yoked_seeds = [master.randint(1, 1_000_000_000) for _ in range(reps)]

    for block in design["blocks"]:
        for honesty_level in block["honesty_levels"]:
            for return_policy in block["return_policies"]:
                policy = design_by_id(design, "return_policies", "return_policy", return_policy)
                for presentation_mode in block["presentation_modes"]:
                    presentation = next(
                        item for item in design["presentation_modes"] if item["presentation_mode"] == presentation_mode
                    )
                    for orthogonality in block["orthogonality_levels"]:
                        for seed_index, local_seed in enumerate(yoked_seeds, start=1):
                            trials = build_trials(design, block, honesty_level, return_policy, local_seed)
                            truth_values = [row["statement_true"] for row in trials if row["statement_true"] is not None]
                            observed_truth_rate = (
                                round(sum(bool(item) for item in truth_values) / len(truth_values), 3)
                                if truth_values
                                else None
                            )
                            runs.append(
                                {
                                    "run_id": run_id,
                                    "block": block["block"],
                                    "block_label": block["label"],
                                    "statement_mode": block["statement_mode"],
                                    "honesty_level": honesty_level,
                                    "return_policy": return_policy,
                                    "return_policy_label": policy["label"],
                                    "presentation_mode": presentation_mode,
                                    "presentation_label": presentation["label"],
                                    "orthogonality_instruction": orthogonality,
                                    "seed_index": seed_index,
                                    "seed": local_seed,
                                    "partner_name": design["partner_name"],
                                    "trials_per_run": int(design["trials_per_run"]),
                                    "observed_truth_rate": observed_truth_rate,
                                    "mean_return_rate": round(
                                        sum(row["return_rate"] for row in trials) / len(trials), 3
                                    ),
                                    "trials": trials,
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

    fallback_patterns = [
        r"['\"]investment['\"]\s*:\s*(-?\d+(?:\.\d+)?)",
        r"\binvestment\s*(?:is|=|:)\s*(-?\d+(?:\.\d+)?)",
        r"\binvest\s+(-?\d+(?:\.\d+)?)\s*(?:tokens?)?",
    ]
    for pattern in fallback_patterns:
        match = re.search(pattern, cleaned, flags=re.I)
        if match:
            return {"investment": float(match.group(1)), "_parse_fallback": True}

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
    response_format_json: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_split:
        payload["reasoning_split"] = True
    if response_format_json:
        payload["response_format"] = {"type": "json_object"}
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
            "Make direct choices. Do not explain, do not analyze, and do not think step by step. "
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
                args.response_format_json,
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


def render_prompt(template_path: Path, run: dict[str, Any], trial: dict[str, Any], compact_history: str | None = None) -> str:
    template = template_path.read_text(encoding="utf-8")
    text = (
        template.replace("{trial_number}", str(trial["trial"]))
        .replace("{trials_per_run}", str(run["trials_per_run"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{orthogonality_note}", orthogonality_note(run["orthogonality_instruction"], run["statement_mode"]))
        .replace("{pre_decision_cue}", build_predecision_cue(run["statement_mode"], run["partner_name"], trial))
    )
    if compact_history is not None:
        text = text.replace("{compact_history}", compact_history)
    return text


def compact_history_text(observed: list[dict[str, Any]]) -> str:
    if not observed:
        payload = {
            "trials_completed": 0,
            "truth_summary": "not available yet",
            "return_summary": "not available yet",
            "previous_investments": [],
            "previous_payoffs": [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    truth_values = [row["statement_true"] for row in observed if row["statement_true"] is not None]
    truth_summary: str | dict[str, Any]
    if truth_values:
        truth_summary = {
            "verifiable_trials": len(truth_values),
            "matched_actual_value": sum(bool(item) for item in truth_values),
            "cumulative_truth_rate": round(sum(bool(item) for item in truth_values) / len(truth_values), 3),
        }
    else:
        truth_summary = "no verifiable statements so far"

    payload = {
        "trials_completed": len(observed),
        "truth_summary": truth_summary,
        "return_summary": {
            "mean_return_rate": round(sum(float(row["return_rate"]) for row in observed) / len(observed), 3),
            "last_return_rate": observed[-1]["return_rate"],
            "mean_returned_tokens": round(sum(float(row["returned_tokens"]) for row in observed) / len(observed), 3),
        },
        "previous_investments": [row["investment"] for row in observed],
        "previous_payoffs": [row["payoff"] for row in observed],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def feedback_message(run: dict[str, Any], result: dict[str, Any]) -> str:
    lines = [
        f"Feedback for trial {result['trial']}:",
        f"You invested {result['investment']} tokens.",
        f"Your investment was tripled to {result['tripled_investment']} tokens.",
        f"{run['partner_name']} returned {result['returned_tokens']} tokens to you.",
        f"Your payoff for this trial was {result['payoff']} tokens.",
    ]
    if result["statement_true"] is not None:
        lines.append(f"The actual side-check value was {result['actual_value']}.")
        lines.append(f"The pre-decision statement matched the actual value: {'yes' if result['statement_true'] else 'no'}.")
    else:
        lines.append("There was no verifiable pre-decision statement on this trial.")
    return "\n".join(lines)


def apply_feedback(trial: dict[str, Any], investment: int) -> dict[str, Any]:
    tripled = investment * 3
    returned = int(round(tripled * float(trial["return_rate"])))
    payoff = 10 - investment + returned
    return {
        **trial,
        "investment": investment,
        "tripled_investment": tripled,
        "returned_tokens": returned,
        "net_gain_from_investment": returned - investment,
        "payoff": payoff,
        "cumulative_truth_rate_before": None,
        "cumulative_return_rate_before": None,
        "previous_payoff": None,
    }


def add_lagged_fields(results: list[dict[str, Any]]) -> None:
    true_so_far = 0
    verifiable_so_far = 0
    return_sum = 0.0
    previous_payoff = None
    for idx, row in enumerate(results):
        if idx == 0:
            row["cumulative_truth_rate_before"] = None
            row["cumulative_return_rate_before"] = None
            row["previous_payoff"] = None
        else:
            row["cumulative_truth_rate_before"] = (
                round(true_so_far / verifiable_so_far, 3) if verifiable_so_far else None
            )
            row["cumulative_return_rate_before"] = round(return_sum / idx, 3)
            row["previous_payoff"] = previous_payoff

        if row["statement_true"] is not None:
            verifiable_so_far += 1
            true_so_far += 1 if row["statement_true"] else 0
        return_sum += float(row["return_rate"])
        previous_payoff = row["payoff"]


def run_sequential(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    messages = [system_message()]
    trial_results = []
    raw_calls = []
    for trial in run["trials"]:
        messages.append({"role": "user", "content": render_prompt(SEQ_PROMPT, run, trial)})
        raw, content, parsed = request_with_retries(messages, args, api_key)
        metrics = trial_metrics(parsed)
        validate_trial_metrics(metrics)
        messages.append({"role": "assistant", "content": json.dumps({"investment": metrics["investment"]})})
        result = apply_feedback(trial, int(metrics["investment"]))
        trial_results.append(result)
        messages.append({"role": "user", "content": feedback_message(run, result)})
        raw_calls.append({"trial": trial["trial"], "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None})
    add_lagged_fields(trial_results)
    return {
        **run,
        "trial_results": trial_results,
        "raw_calls": raw_calls,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": len(run["trials"]),
        "model": args.model,
    }


def run_evidence_only(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    observed = []
    raw_calls = []
    for trial in run["trials"]:
        prompt = render_prompt(EVIDENCE_PROMPT, run, trial, compact_history_text(observed))
        messages = [system_message(), {"role": "user", "content": prompt}]
        raw, content, parsed = request_with_retries(messages, args, api_key)
        metrics = trial_metrics(parsed)
        validate_trial_metrics(metrics)
        result = apply_feedback(trial, int(metrics["investment"]))
        observed.append(result)
        raw_calls.append({"trial": trial["trial"], "content": content, "parsed": parsed, "raw": raw if args.keep_raw else None})
    add_lagged_fields(observed)
    return {
        **run,
        "trial_results": observed,
        "raw_calls": raw_calls,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": len(run["trials"]),
        "model": args.model,
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260528)
    parser.add_argument("--seeds-per-cell", type=int, default=None)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--reasoning-split", action="store_true")
    parser.add_argument("--response-format-json", action="store_true")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--block", default=None)
    parser.add_argument("--presentation", default=None)
    parser.add_argument("--return-policy", default=None)
    parser.add_argument("--force-rerun", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    runs = build_runs(args.seed, args.seeds_per_cell)
    write_json(OUT / "run_conditions.json", runs)
    if args.dry_run:
        print(f"Wrote {OUT / 'run_conditions.json'}")
        print(f"Runs: {len(runs)}")
        print(f"Trial decisions: {sum(len(run['trials']) for run in runs)}")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    filtered = []
    for run in runs:
        if args.block and run["block"] != args.block:
            continue
        if args.presentation and run["presentation_mode"] != args.presentation:
            continue
        if args.return_policy and run["return_policy"] != args.return_policy:
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
                f"[{status}] run={result['run_id']:03d} {result['block']} "
                f"{result['honesty_level']} {result['return_policy']} "
                f"{result['presentation_mode']} mean_inv={mean_inv}"
            )

    sorted_results = sorted(results_by_id.values(), key=lambda item: item["run_id"])
    write_json(results_path, sorted_results)
    print(f"Wrote {results_path}")


if __name__ == "__main__":
    main()
