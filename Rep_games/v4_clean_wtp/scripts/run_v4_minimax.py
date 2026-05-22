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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
PROMPT_TEMPLATE = ROOT / "prompts" / "clean_wtp_prompt.md"
DESIGN_PATH = ROOT / "conditions" / "factorial_design.json"
ANTHROPIC_API_URL = "https://api.minimaxi.com/anthropic/v1/messages"
DEFAULT_MODEL = "MiniMax-M2.7"
MAX_INVESTMENT = {"low": 4, "medium": 7, "high": 10}
BASE_BY_STAKE = {"low": 0.55, "medium": 0.40, "high": 0.25}
REPAIRING_BY_ROUND = [0.25, 0.30, 0.35, 0.45, 0.50, 0.55]
DETERIORATING_BY_ROUND = list(reversed(REPAIRING_BY_ROUND))


@dataclass(frozen=True)
class Trial:
    trial_id: int
    history_id: str
    behavior_pattern: str
    behavior_label: str
    language_frame: str
    language_label: str
    next_stake: str
    max_investment: int
    history: list[dict[str, Any]]
    prompt: str
    average_return_fraction: float
    low_stake_return_fraction: float | None
    medium_stake_return_fraction: float | None
    high_stake_return_fraction: float | None
    final_two_return_fraction: float
    generated_policy_return_for_next_stake: float


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_design() -> dict[str, Any]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def zero_sum_noise(rng: random.Random, n: int, scale: float) -> list[float]:
    values = [rng.uniform(-scale, scale) for _ in range(n)]
    shift = sum(values) / n
    return [v - shift for v in values]


def correct_mean(values: list[float], target: float = 0.40) -> list[float]:
    diff = sum(values) / len(values) - target
    corrected = [clip(v - diff, 0.15, 0.65) for v in values]
    diff = sum(corrected) / len(corrected) - target
    return [round(clip(v - diff, 0.15, 0.65), 3) for v in corrected]


def base_returns(behavior_pattern: str, stakes: list[str]) -> list[float]:
    if behavior_pattern == "stable_moderate":
        return [0.40 for _ in stakes]
    if behavior_pattern == "strategic_opportunist":
        return [BASE_BY_STAKE[s] for s in stakes]
    if behavior_pattern == "noisy_repairing":
        return REPAIRING_BY_ROUND.copy()
    if behavior_pattern == "deteriorating_exploiter":
        return DETERIORATING_BY_ROUND.copy()
    raise ValueError(behavior_pattern)


def policy_return_for_next(behavior_pattern: str, next_stake: str) -> float:
    if behavior_pattern == "stable_moderate":
        return 0.40
    if behavior_pattern == "strategic_opportunist":
        return BASE_BY_STAKE[next_stake]
    if behavior_pattern == "noisy_repairing":
        return 0.55
    if behavior_pattern == "deteriorating_exploiter":
        return 0.25
    raise ValueError(behavior_pattern)


def noisy_returns(behavior_pattern: str, stakes: list[str], rng: random.Random) -> list[float]:
    base = base_returns(behavior_pattern, stakes)
    noise = zero_sum_noise(rng, len(base), 0.035)
    values = [clip(b + e, 0.15, 0.65) for b, e in zip(base, noise)]
    return correct_mean(values)


def build_numeric_history(behavior_pattern: str, stakes: list[str], rng: random.Random) -> list[dict[str, Any]]:
    fractions = noisy_returns(behavior_pattern, stakes, rng)
    history = []
    for round_index, (stake, frac) in enumerate(zip(stakes, fractions), start=1):
        invested = MAX_INVESTMENT[stake]
        received = invested * 3
        returned = round(received * frac, 2)
        history.append(
            {
                "round": round_index,
                "stake": stake,
                "previous_participant_invested": invested,
                "partner_received": received,
                "partner_returned": returned,
                "return_fraction": round(returned / received, 3),
            }
        )
    return history


def attach_language(history: list[dict[str, Any]], message: str) -> list[dict[str, Any]]:
    return [{**row, "partner_message": message} for row in history]


def history_to_text(history: list[dict[str, Any]]) -> str:
    lines = []
    for row in history:
        lines.append(
            f"Round {row['round']} ({row['stake']} stake): Partner says, \"{row['partner_message']}\" "
            f"The previous participant invested {row['previous_participant_invested']} tokens. "
            f"The partner received {row['partner_received']} and returned {row['partner_returned']} tokens."
        )
    return "\n".join(lines)


def make_prompt(history: list[dict[str, Any]], next_stake: str) -> str:
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return (
        template.replace("{history}", history_to_text(history))
        .replace("{next_stake}", next_stake)
        .replace("{max_investment}", str(MAX_INVESTMENT[next_stake]))
    )


def stake_mean(history: list[dict[str, Any]], stake: str) -> float | None:
    values = [row["return_fraction"] for row in history if row["stake"] == stake]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_trials(histories_per_behavior: int, seed: int) -> list[Trial]:
    rng = random.Random(seed)
    design = load_design()
    numeric_histories: list[dict[str, Any]] = []
    for behavior in design["behavior_patterns"]:
        for idx in range(histories_per_behavior):
            stakes = design["stake_orders"][idx % len(design["stake_orders"])]
            next_stake = design["next_stakes"][idx % len(design["next_stakes"])]
            local_rng = random.Random(rng.randint(0, 10_000_000))
            history = build_numeric_history(behavior["behavior_pattern"], stakes, local_rng)
            numeric_histories.append(
                {
                    "history_id": f"{behavior['behavior_pattern']}_{idx + 1:02d}",
                    "behavior_pattern": behavior["behavior_pattern"],
                    "behavior_label": behavior["label"],
                    "next_stake": next_stake,
                    "history": history,
                    "generated_policy_return_for_next_stake": policy_return_for_next(behavior["behavior_pattern"], next_stake),
                }
            )

    trials: list[Trial] = []
    trial_id = 1
    for numeric in numeric_histories:
        for language in design["language_frames"]:
            history = attach_language(numeric["history"], language["message"])
            trials.append(
                Trial(
                    trial_id=trial_id,
                    history_id=numeric["history_id"],
                    behavior_pattern=numeric["behavior_pattern"],
                    behavior_label=numeric["behavior_label"],
                    language_frame=language["language_frame"],
                    language_label=language["label"],
                    next_stake=numeric["next_stake"],
                    max_investment=MAX_INVESTMENT[numeric["next_stake"]],
                    history=history,
                    prompt=make_prompt(history, numeric["next_stake"]),
                    average_return_fraction=round(sum(row["return_fraction"] for row in history) / len(history), 4),
                    low_stake_return_fraction=stake_mean(history, "low"),
                    medium_stake_return_fraction=stake_mean(history, "medium"),
                    high_stake_return_fraction=stake_mean(history, "high"),
                    final_two_return_fraction=round(sum(row["return_fraction"] for row in history[-2:]) / 2, 4),
                    generated_policy_return_for_next_stake=numeric["generated_policy_return_for_next_stake"],
                )
            )
            trial_id += 1
    rng.shuffle(trials)
    return [
        Trial(
            trial_id=i + 1,
            history_id=t.history_id,
            behavior_pattern=t.behavior_pattern,
            behavior_label=t.behavior_label,
            language_frame=t.language_frame,
            language_label=t.language_label,
            next_stake=t.next_stake,
            max_investment=t.max_investment,
            history=t.history,
            prompt=t.prompt,
            average_return_fraction=t.average_return_fraction,
            low_stake_return_fraction=t.low_stake_return_fraction,
            medium_stake_return_fraction=t.medium_stake_return_fraction,
            high_stake_return_fraction=t.high_stake_return_fraction,
            final_two_return_fraction=t.final_two_return_fraction,
            generated_policy_return_for_next_stake=t.generated_policy_return_for_next_stake,
        )
        for i, t in enumerate(trials)
    ]


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str) -> dict[str, Any]:
    text = strip_thinking(text)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def call_minimax_anthropic(prompt: str, api_key: str, model: str, timeout: int, max_tokens: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "system": "Return only the final JSON object requested by the user. Do not include reasoning, analysis, markdown, or any text outside the JSON object.",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Connection": "close",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def extract_content(raw: dict[str, Any]) -> str:
    content = raw.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return ""


def clean_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"true", "yes", "continue", "1"}:
            return True
        if lower in {"false", "no", "skip", "0"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def clean_num(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return clip(number, low, high)


def metrics(parsed: dict[str, Any], max_investment: int) -> dict[str, Any]:
    continue_choice = clean_bool(parsed.get("continue_choice"))
    wtp = clean_num(parsed.get("willingness_to_pay"), 0, 10)
    next_investment = clean_num(parsed.get("next_investment"), 0, max_investment)
    trust = clean_num(parsed.get("trust_rating"), 0, 100)
    output = {
        "continue_choice": continue_choice,
        "willingness_to_pay": None if wtp is None else int(round(wtp)),
        "next_investment": None if next_investment is None else int(round(next_investment)),
        "investment_fraction": None if next_investment is None or max_investment == 0 else round(next_investment / max_investment, 3),
        "trust_rating": None if trust is None else int(round(trust)),
    }
    return output


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_resume_results() -> list[dict[str, Any]]:
    for name in ["results_partial.json", "results.json"]:
        path = OUT / name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--histories-per-behavior", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=10.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-errors", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    trials = build_trials(args.histories_per_behavior, args.seed)
    save_json(OUT / "trial_conditions.json", [asdict(t) for t in trials])
    if args.dry_run:
        print(f"Generated {len(trials)} trial conditions.")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    if args.resume:
        loaded_results = load_resume_results()
        existing_results = loaded_results if args.skip_errors else [row for row in loaded_results if not row.get("error")]
    else:
        existing_results = []
    completed_ids = {row.get("trial_id") for row in existing_results if row.get("trial_id") is not None}
    selected = [trial for trial in trials if trial.trial_id not in completed_ids]
    if args.max_calls:
        selected = selected[: args.max_calls]
    results = existing_results.copy()
    for i, trial in enumerate(selected, start=1):
        error = None
        raw_content = ""
        parsed: dict[str, Any] = {}
        m: dict[str, Any] = {}
        start = time.time()
        attempts = 0
        for attempt in range(args.retries + 1):
            attempts = attempt + 1
            error = None
            try:
                raw = call_minimax_anthropic(trial.prompt, api_key, args.model, args.timeout, args.max_tokens)
                raw_content = extract_content(raw)
                parsed = extract_json(raw_content)
                m = metrics(parsed, trial.max_investment)
                break
            except Exception as exc:
                error = repr(exc)
                if "HTTP 429" in error or attempt >= args.retries:
                    break
                time.sleep(args.retry_sleep)
        row = {
            **asdict(trial),
            "raw_content": raw_content,
            "parsed": parsed,
            "metrics": m,
            "error": error,
            "attempts": attempts,
            "latency_sec": round(time.time() - start, 3),
        }
        results.append(row)
        save_json(OUT / "results_partial.json", results)
        status = "error" if error else f"wtp={m.get('willingness_to_pay')} invest={m.get('next_investment')} trust={m.get('trust_rating')}"
        print(f"[{i}/{len(selected)}] trial_id={trial.trial_id} {trial.behavior_pattern}/{trial.language_frame}/{trial.next_stake}: {status}", flush=True)
        if error and "HTTP 429" in error:
            print("Rate limit detected; stopping early.", flush=True)
            break
        time.sleep(args.sleep)
    save_json(OUT / "results.json", results)


if __name__ == "__main__":
    main()
