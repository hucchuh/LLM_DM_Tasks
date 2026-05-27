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
SEQ_OBS_PROMPT = ROOT / "prompts" / "sequential_observation_prompt.md"
MAIN_DECISION_PROMPT = ROOT / "prompts" / "main_decision_prompt.md"
BATCH_MAIN_PROMPT = ROOT / "prompts" / "batch_main_prompt.md"
PROBE_PROMPT = ROOT / "prompts" / "probe_prompt.md"

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


def choose_false_value(actual_value: int, rng: random.Random) -> int:
    candidates = [value for value in range(1, 10) if value != actual_value]
    return rng.choice(candidates)


def build_episodes(partner: dict[str, Any], rounds: int, seed: int, partner_name: str) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    honesty_flags = exact_flags(int(partner["honesty_true_count"]), rounds, rng)
    win_flags = exact_flags(int(partner["recommendation_win_count"]), rounds, rng)
    episodes = []

    for idx, (is_honest, recommendation_wins) in enumerate(zip(honesty_flags, win_flags), start=1):
        recommended_side = rng.choice(["left", "right"])
        other = other_side(recommended_side)
        high = rng.choice([7, 8, 9])
        low = rng.choice([1, 2, 3])
        actual = {recommended_side: high, other: low} if recommendation_wins else {recommended_side: low, other: high}
        actual_checked_value = actual[recommended_side]
        stated_value = actual_checked_value if is_honest else choose_false_value(actual_checked_value, rng)
        partner_message = (
            f"I checked the {recommended_side} card. It is {stated_value}. "
            f"I recommend choosing {recommended_side}."
        )
        episodes.append(
            {
                "round": idx,
                "partner_name": partner_name,
                "partner_message": partner_message,
                "checked_side": recommended_side,
                "recommended_side": recommended_side,
                "stated_value": stated_value,
                "actual_left": actual["left"],
                "actual_right": actual["right"],
                "actual_checked_value": actual_checked_value,
                "statement_honest": is_honest,
                "recommendation_wins": recommendation_wins,
            }
        )
    return episodes


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
                episodes = build_episodes(partner, rounds, local_seed, partner_name)
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
                        "episodes": episodes,
                        "observed_honesty_rate": round(sum(ep["statement_honest"] for ep in episodes) / rounds, 3),
                        "observed_recommendation_win_rate": round(sum(ep["recommendation_wins"] for ep in episodes) / rounds, 3),
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
            parsed_candidate = ast.literal_eval(trimmed)
            if isinstance(parsed_candidate, dict):
                return parsed_candidate
        except (SyntaxError, ValueError) as exc:
            last_exc = exc
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        if last_exc is not None:
            raise last_exc
        parsed = ast.literal_eval(cleaned)
        if not isinstance(parsed, dict):
            raise
        return parsed


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


def clean_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y"}:
            return True
        if lowered in {"false", "no", "n"}:
            return False
    return None


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


def main_metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "enter_choice": clean_bool(parsed.get("enter_choice")),
        "willingness_to_pay": clean_int(parsed.get("willingness_to_pay"), 0, 10),
        "investment": clean_int(parsed.get("investment"), 0, 10),
    }


def probe_metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "perceived_honesty": clean_int(parsed.get("perceived_honesty"), 0, 100),
        "perceived_helpfulness": clean_int(parsed.get("perceived_helpfulness"), 0, 100),
        "expected_recommendation_win_rate": clean_float(parsed.get("expected_recommendation_win_rate"), 0, 1),
        "moral_trust": clean_int(parsed.get("moral_trust"), 0, 100),
        "brief_reason": parsed.get("brief_reason", ""),
    }


def validate_main_metrics(metrics: dict[str, Any]) -> None:
    missing = [key for key in ["enter_choice", "willingness_to_pay", "investment"] if metrics.get(key) is None]
    if missing:
        raise ValueError(f"Missing main decision fields: {missing}")


def validate_probe_metrics(metrics: dict[str, Any]) -> None:
    missing = [
        key
        for key in ["perceived_honesty", "perceived_helpfulness", "expected_recommendation_win_rate", "moral_trust"]
        if metrics.get(key) is None
    ]
    if missing:
        raise ValueError(f"Missing probe fields: {missing}")


def observation_prompt(run: dict[str, Any], episode: dict[str, Any]) -> str:
    template = SEQ_OBS_PROMPT.read_text(encoding="utf-8")
    return (
        template.replace("{round_number}", str(episode["round"]))
        .replace("{rounds_per_run}", str(run["rounds_per_run"]))
        .replace("{partner_name}", run["partner_name"])
        .replace("{partner_message}", episode["partner_message"])
        .replace("{actual_left}", str(episode["actual_left"]))
        .replace("{actual_right}", str(episode["actual_right"]))
        .replace("{statement_truth}", "true" if episode["statement_honest"] else "false")
        .replace("{recommendation_result}", "would have won" if episode["recommendation_wins"] else "would have lost")
    )


def main_decision_prompt(run: dict[str, Any]) -> str:
    template = MAIN_DECISION_PROMPT.read_text(encoding="utf-8")
    return template.replace("{rounds_per_run}", str(run["rounds_per_run"])).replace("{partner_name}", run["partner_name"])


def history_text(run: dict[str, Any]) -> str:
    lines = []
    for ep in run["episodes"]:
        lines.append(
            f"Round {ep['round']}: {run['partner_name']} said, \"{ep['partner_message']}\" "
            f"Left={ep['actual_left']}, right={ep['actual_right']}. "
            f"The factual statement was {'true' if ep['statement_honest'] else 'false'}; "
            f"the recommendation {'would have won' if ep['recommendation_wins'] else 'would have lost'}."
        )
    return "\n".join(lines)


def batch_main_prompt(run: dict[str, Any]) -> str:
    template = BATCH_MAIN_PROMPT.read_text(encoding="utf-8")
    return template.replace("{partner_name}", run["partner_name"]).replace("{history}", history_text(run))


def probe_prompt(run: dict[str, Any]) -> str:
    template = PROBE_PROMPT.read_text(encoding="utf-8")
    return template.replace("{partner_name}", run["partner_name"]).replace("{history}", history_text(run))


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


def system_message() -> dict[str, str]:
    return {
        "role": "system",
        "content": "You are a participant in a behavioral decision-making experiment. Answer only with valid JSON when asked.",
    }


def run_probe(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    messages = [system_message(), {"role": "user", "content": probe_prompt(run)}]
    raw, content, parsed = request_with_retries(messages, args, api_key)
    metrics = probe_metrics(parsed)
    validate_probe_metrics(metrics)
    return {
        "probe_raw_content": content,
        "probe_parsed": parsed,
        "probe_metrics": metrics,
        "probe_raw": raw if args.keep_raw else None,
    }


def run_sequential(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    messages = [system_message()]
    observations = []

    for ep in run["episodes"]:
        messages.append({"role": "user", "content": observation_prompt(run, ep)})
        raw, content, parsed = request_with_retries(messages, args, api_key)
        messages.append({"role": "assistant", "content": content})
        observations.append(
            {
                **ep,
                "observation_raw_content": content,
                "observation_parsed": parsed,
                "observation_raw": raw if args.keep_raw else None,
            }
        )

    messages.append({"role": "user", "content": main_decision_prompt(run)})
    raw, content, parsed = request_with_retries(messages, args, api_key)
    metrics = main_metrics(parsed)
    validate_main_metrics(metrics)
    probe = run_probe(run, args, api_key) if not args.skip_probe else {"probe_metrics": {}}

    return {
        **run,
        "observation_results": observations,
        "main_raw_content": content,
        "main_parsed": parsed,
        "main_metrics": metrics,
        "main_raw": raw if args.keep_raw else None,
        **probe,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": len(run["episodes"]) + 1 + (0 if args.skip_probe else 1),
    }


def run_batch(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    started = time.time()
    messages = [system_message(), {"role": "user", "content": batch_main_prompt(run)}]
    raw, content, parsed = request_with_retries(messages, args, api_key)
    metrics = main_metrics(parsed)
    validate_main_metrics(metrics)
    probe = run_probe(run, args, api_key) if not args.skip_probe else {"probe_metrics": {}}

    return {
        **run,
        "observation_results": [],
        "main_raw_content": content,
        "main_parsed": parsed,
        "main_metrics": metrics,
        "main_raw": raw if args.keep_raw else None,
        **probe,
        "error": None,
        "latency_sec": round(time.time() - started, 3),
        "n_api_calls": 1 + (0 if args.skip_probe else 1),
    }


def run_one(run: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    try:
        if run["presentation_mode"] == "sequential_observation":
            return run_sequential(run, args, api_key)
        return run_batch(run, args, api_key)
    except Exception as exc:
        return {
            **run,
            "observation_results": [],
            "main_metrics": {},
            "probe_metrics": {},
            "error": str(exc),
            "latency_sec": None,
            "n_api_calls": 0,
        }


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_resume_results(results_path: Path, partial_path: Path) -> list[dict[str, Any]]:
    if results_path.exists():
        return load_existing(results_path)
    return load_existing(partial_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--seeds-per-cell", type=int, default=None)
    parser.add_argument("--rounds-per-run", type=int, default=None)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--reasoning-split", action="store_true")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-probe", action="store_true")
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N remaining runs.")
    parser.add_argument("--min-run", type=int, default=None, help="Only run conditions with run_id >= this value.")
    parser.add_argument("--max-run", type=int, default=None, help="Only run conditions with run_id <= this value.")
    parser.add_argument("--partner", default=None, help="Only run one partner_type.")
    parser.add_argument("--mode", default=None, help="Only run one presentation_mode.")
    parser.add_argument("--force-rerun", action="store_true", help="Run filtered runs even if they already have a successful result.")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    runs = build_runs(args.seed, args.seeds_per_cell, args.rounds_per_run)
    write_json(OUT / "run_conditions.json", runs)

    if args.dry_run:
        print(f"Wrote {OUT / 'run_conditions.json'}")
        print(f"Runs: {len(runs)}")
        return

    filtered_runs = []
    for run in runs:
        if args.min_run is not None and run["run_id"] < args.min_run:
            continue
        if args.max_run is not None and run["run_id"] > args.max_run:
            continue
        if args.partner is not None and run["partner_type"] != args.partner:
            continue
        if args.mode is not None and run["presentation_mode"] != args.mode:
            continue
        filtered_runs.append(run)

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    results_path = OUT / "results.json"
    partial_path = OUT / "results_partial.json"
    existing = load_resume_results(results_path, partial_path) if args.resume else []
    done_ids = {item["run_id"] for item in existing if not item.get("error")}
    todo = filtered_runs if args.force_rerun else [run for run in filtered_runs if run["run_id"] not in done_ids]
    if args.limit is not None:
        todo = todo[: args.limit]
    results_by_id = {item["run_id"]: item for item in existing}

    print(f"Total runs: {len(runs)}")
    print(f"Filtered runs: {len(filtered_runs)}")
    print(f"Completed successful runs: {len(done_ids)}")
    print(f"Remaining runs: {len(todo)}")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(run_one, run, args, api_key): run for run in todo}
        for future in as_completed(futures):
            result = future.result()
            results_by_id[result["run_id"]] = result
            write_json(partial_path, sorted(results_by_id.values(), key=lambda row: row["run_id"]))
            status = "OK" if not result.get("error") else "ERR"
            m = result.get("main_metrics") or {}
            p = result.get("probe_metrics") or {}
            print(
                f"[{status}] run={result['run_id']:03d} {result['partner_type']} {result['presentation_mode']} "
                f"wtp={m.get('willingness_to_pay')} inv={m.get('investment')} "
                f"honesty={p.get('perceived_honesty')} helpful={p.get('perceived_helpfulness')}"
            )

    sorted_results = sorted(results_by_id.values(), key=lambda row: row["run_id"])
    write_json(results_path, sorted_results)
    print(f"Wrote {results_path}")


if __name__ == "__main__":
    main()
