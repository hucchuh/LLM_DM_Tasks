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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
PROMPT_TEMPLATE = ROOT / "prompts" / "v5_prompt.md"
DESIGN_PATH = ROOT / "conditions" / "design.json"
DEFAULT_ENDPOINT = "https://lightingtheword.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"
MAX_INVESTMENT = {"low": 4, "medium": 7, "high": 10}
BASE_BY_STAKE = {"low": 0.55, "medium": 0.40, "high": 0.25}


@dataclass(frozen=True)
class Trial:
    trial_id: int
    history_id: str
    partner_type: str
    partner_label: str
    control_condition: str
    control_label: str
    history: list[dict[str, Any]]
    prompt: str
    average_return_fraction: float
    low_stake_return_fraction: float | None
    medium_stake_return_fraction: float | None
    high_stake_return_fraction: float | None
    low_minus_high_return_fraction: float | None
    return_sd: float


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_existing_results() -> list[dict[str, Any]]:
    candidates = [
        load_json(OUT / "results.json", []),
        load_json(OUT / "results_partial.json", []),
        load_json(OUT / "results_partial_new.json", []),
    ]
    return max(candidates, key=lambda rows: (sum(1 for row in rows if not row.get("error")), len(rows)))


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def zero_sum_noise(rng: random.Random, n: int, scale: float) -> list[float]:
    values = [rng.uniform(-scale, scale) for _ in range(n)]
    shift = sum(values) / n
    return [v - shift for v in values]


def correct_mean(values: list[float], target: float = 0.40) -> list[float]:
    diff = sum(values) / len(values) - target
    corrected = [clip(v - diff, 0.12, 0.68) for v in values]
    diff = sum(corrected) / len(corrected) - target
    return [round(clip(v - diff, 0.12, 0.68), 3) for v in corrected]


def base_returns(partner_type: str, stakes: list[str], rng: random.Random) -> list[float]:
    if partner_type == "stable_cooperator":
        base = [0.40 for _ in stakes]
        noise = zero_sum_noise(rng, len(base), 0.03)
        return correct_mean([b + e for b, e in zip(base, noise)])

    if partner_type == "predictable_opportunist":
        base = [BASE_BY_STAKE[s] for s in stakes]
        noise = zero_sum_noise(rng, len(base), 0.025)
        return correct_mean([b + e for b, e in zip(base, noise)])

    if partner_type == "random_opportunist":
        values = [0.55, 0.55, 0.40, 0.40, 0.25, 0.25]
        for _ in range(200):
            shuffled = values.copy()
            rng.shuffle(shuffled)
            candidate = correct_mean([v + e for v, e in zip(shuffled, zero_sum_noise(rng, 6, 0.025))])
            low = stake_mean_from_values(stakes, candidate, "low")
            high = stake_mean_from_values(stakes, candidate, "high")
            if low is not None and high is not None and abs(low - high) <= 0.10:
                return candidate
        return correct_mean(values)

    raise ValueError(partner_type)


def stake_mean_from_values(stakes: list[str], values: list[float], stake: str) -> float | None:
    subset = [v for s, v in zip(stakes, values) if s == stake]
    if not subset:
        return None
    return round(sum(subset) / len(subset), 4)


def build_history(partner_type: str, stakes: list[str], message: str, rng: random.Random) -> list[dict[str, Any]]:
    fractions = base_returns(partner_type, stakes, rng)
    rows = []
    for index, (stake, frac) in enumerate(zip(stakes, fractions), start=1):
        invested = MAX_INVESTMENT[stake]
        received = invested * 3
        returned = round(received * frac, 2)
        rows.append(
            {
                "round": index,
                "stake": stake,
                "partner_message": message,
                "previous_participant_invested": invested,
                "partner_received": received,
                "partner_returned": returned,
                "return_fraction": round(returned / received, 3),
            }
        )
    return rows


def history_to_text(history: list[dict[str, Any]]) -> str:
    lines = []
    for row in history:
        lines.append(
            f"Round {row['round']} ({row['stake']} stake): Partner says, \"{row['partner_message']}\" "
            f"The previous participant invested {row['previous_participant_invested']} tokens. "
            f"The partner received {row['partner_received']} and returned {row['partner_returned']} tokens."
        )
    return "\n".join(lines)


def control_parts(control_condition: str) -> tuple[str, str, str]:
    if control_condition == "controllable_stake":
        instruction = (
            "For the next round, you may choose whether it will be a low-stake, medium-stake, or high-stake round. "
            "After choosing the stake level, choose how many tokens to invest within that stake's maximum."
        )
        schema = """{
  "continue_choice": true,
  "willingness_to_pay": 0,
  "chosen_stake": "low",
  "next_investment": 0,
  "trust_rating": 0,
  "predicted_return_fraction_if_low_stake": 0.0,
  "predicted_return_fraction_if_medium_stake": 0.0,
  "predicted_return_fraction_if_high_stake": 0.0,
  "brief_reason": "one short sentence"
}"""
        rules = (
            '- chosen_stake must be "low", "medium", or "high".\n'
            "- next_investment is an integer from 0 to the maximum investment allowed by chosen_stake."
        )
        return instruction, schema, rules

    if control_condition == "fixed_high_stake":
        instruction = (
            "A new high-stake round is about to begin with this same partner. "
            "You may invest any integer amount from 0 to 10 tokens."
        )
        schema = """{
  "continue_choice": true,
  "willingness_to_pay": 0,
  "next_investment": 0,
  "trust_rating": 0,
  "predicted_return_fraction_if_low_stake": 0.0,
  "predicted_return_fraction_if_medium_stake": 0.0,
  "predicted_return_fraction_if_high_stake": 0.0,
  "brief_reason": "one short sentence"
}"""
        rules = "- next_investment is an integer from 0 to 10."
        return instruction, schema, rules

    if control_condition == "random_stake":
        instruction = (
            "After you pay for access, the next round's stake level will be randomly selected with equal probability "
            "from low, medium, and high. You cannot control which stake level occurs, but you may plan how much you "
            "would invest under each possible stake."
        )
        schema = """{
  "continue_choice": true,
  "willingness_to_pay": 0,
  "investment_if_low_stake": 0,
  "investment_if_medium_stake": 0,
  "investment_if_high_stake": 0,
  "trust_rating": 0,
  "predicted_return_fraction_if_low_stake": 0.0,
  "predicted_return_fraction_if_medium_stake": 0.0,
  "predicted_return_fraction_if_high_stake": 0.0,
  "brief_reason": "one short sentence"
}"""
        rules = (
            "- investment_if_low_stake is an integer from 0 to 4.\n"
            "- investment_if_medium_stake is an integer from 0 to 7.\n"
            "- investment_if_high_stake is an integer from 0 to 10."
        )
        return instruction, schema, rules

    raise ValueError(control_condition)


def make_prompt(history: list[dict[str, Any]], control_condition: str) -> str:
    instruction, schema, rules = control_parts(control_condition)
    template = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return (
        template.replace("{history}", history_to_text(history))
        .replace("{control_instruction}", instruction)
        .replace("{json_schema}", schema)
        .replace("{field_rules}", rules)
    )


def stake_mean(history: list[dict[str, Any]], stake: str) -> float | None:
    values = [row["return_fraction"] for row in history if row["stake"] == stake]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_trials(histories_per_partner: int, seed: int) -> list[Trial]:
    rng = random.Random(seed)
    design = load_json(DESIGN_PATH, {})
    numeric_histories = []
    for partner in design["partner_types"]:
        for idx in range(histories_per_partner):
            stakes = design["stake_orders"][idx % len(design["stake_orders"])]
            local_rng = random.Random(rng.randint(0, 10_000_000))
            history = build_history(partner["partner_type"], stakes, design["partner_message"], local_rng)
            low = stake_mean(history, "low")
            high = stake_mean(history, "high")
            numeric_histories.append(
                {
                    "history_id": f"{partner['partner_type']}_{idx + 1:02d}",
                    "partner_type": partner["partner_type"],
                    "partner_label": partner["label"],
                    "history": history,
                    "average_return_fraction": round(sum(row["return_fraction"] for row in history) / len(history), 4),
                    "low_stake_return_fraction": low,
                    "medium_stake_return_fraction": stake_mean(history, "medium"),
                    "high_stake_return_fraction": high,
                    "low_minus_high_return_fraction": None if low is None or high is None else round(low - high, 4),
                    "return_sd": round(math.sqrt(sum((row["return_fraction"] - 0.4) ** 2 for row in history) / len(history)), 4),
                }
            )

    trials = []
    trial_id = 1
    for item in numeric_histories:
        for control in design["control_conditions"]:
            trials.append(
                Trial(
                    trial_id=trial_id,
                    history_id=item["history_id"],
                    partner_type=item["partner_type"],
                    partner_label=item["partner_label"],
                    control_condition=control["control_condition"],
                    control_label=control["label"],
                    history=item["history"],
                    prompt=make_prompt(item["history"], control["control_condition"]),
                    average_return_fraction=item["average_return_fraction"],
                    low_stake_return_fraction=item["low_stake_return_fraction"],
                    medium_stake_return_fraction=item["medium_stake_return_fraction"],
                    high_stake_return_fraction=item["high_stake_return_fraction"],
                    low_minus_high_return_fraction=item["low_minus_high_return_fraction"],
                    return_sd=item["return_sd"],
                )
            )
            trial_id += 1
    rng.shuffle(trials)
    return [Trial(**{**asdict(t), "trial_id": i + 1}) for i, t in enumerate(trials)]


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str) -> dict[str, Any]:
    text = strip_thinking(text)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def clean_num(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return clip(number, low, high)


def clean_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def clean_stake(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in MAX_INVESTMENT:
        return lowered
    return None


def metrics(parsed: dict[str, Any], control_condition: str) -> dict[str, Any]:
    continue_choice = clean_bool(parsed.get("continue_choice"))
    wtp = clean_num(parsed.get("willingness_to_pay"), 0, 10)
    trust = clean_num(parsed.get("trust_rating"), 0, 100)
    pred_low = clean_num(parsed.get("predicted_return_fraction_if_low_stake"), 0, 1)
    pred_medium = clean_num(parsed.get("predicted_return_fraction_if_medium_stake"), 0, 1)
    pred_high = clean_num(parsed.get("predicted_return_fraction_if_high_stake"), 0, 1)

    chosen_stake = None
    next_investment = None
    investment_fraction = None
    random_mean_investment_fraction = None
    low_investment_fraction = None
    medium_investment_fraction = None
    high_investment_fraction = None

    if control_condition == "controllable_stake":
        chosen_stake = clean_stake(parsed.get("chosen_stake"))
        max_inv = MAX_INVESTMENT.get(chosen_stake or "", 10)
        next_investment = clean_num(parsed.get("next_investment"), 0, max_inv)
        investment_fraction = None if next_investment is None or chosen_stake is None else round(next_investment / max_inv, 3)
    elif control_condition == "fixed_high_stake":
        chosen_stake = "high"
        next_investment = clean_num(parsed.get("next_investment"), 0, 10)
        investment_fraction = None if next_investment is None else round(next_investment / 10, 3)
    elif control_condition == "random_stake":
        low_inv = clean_num(parsed.get("investment_if_low_stake"), 0, 4)
        med_inv = clean_num(parsed.get("investment_if_medium_stake"), 0, 7)
        high_inv = clean_num(parsed.get("investment_if_high_stake"), 0, 10)
        low_investment_fraction = None if low_inv is None else round(low_inv / 4, 3)
        medium_investment_fraction = None if med_inv is None else round(med_inv / 7, 3)
        high_investment_fraction = None if high_inv is None else round(high_inv / 10, 3)
        values = [v for v in [low_investment_fraction, medium_investment_fraction, high_investment_fraction] if v is not None]
        random_mean_investment_fraction = None if not values else round(sum(values) / len(values), 3)
        investment_fraction = random_mean_investment_fraction

    return {
        "continue_choice": continue_choice,
        "willingness_to_pay": None if wtp is None else int(round(wtp)),
        "chosen_stake": chosen_stake,
        "next_investment": None if next_investment is None else int(round(next_investment)),
        "investment_fraction": investment_fraction,
        "random_mean_investment_fraction": random_mean_investment_fraction,
        "low_investment_fraction": low_investment_fraction,
        "medium_investment_fraction": medium_investment_fraction,
        "high_investment_fraction": high_investment_fraction,
        "trust_rating": None if trust is None else int(round(trust)),
        "predicted_return_fraction_if_low_stake": pred_low,
        "predicted_return_fraction_if_medium_stake": pred_medium,
        "predicted_return_fraction_if_high_stake": pred_high,
        "predicted_low_minus_high": None if pred_low is None or pred_high is None else round(pred_low - pred_high, 3),
    }


def extract_content(raw: dict[str, Any]) -> str:
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            content = content.strip()
            if content:
                return content
        reasoning_content = message.get("reasoning_content", "")
        if isinstance(reasoning_content, str):
            return reasoning_content.strip()
    return ""


def call_openai_compatible(prompt: str, api_key: str, endpoint: str, model: str, timeout: int, max_tokens: int, temperature: float) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only the final JSON object requested by the user. Do not include markdown or any text outside the JSON object."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json", "Connection": "close"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def run_one(trial: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    start = time.time()
    raw_content = ""
    parsed: dict[str, Any] = {}
    m: dict[str, Any] = {}
    error = None
    attempts = 0
    for attempt in range(args.retries + 1):
        attempts = attempt + 1
        error = None
        try:
            raw = call_openai_compatible(trial["prompt"], api_key, args.endpoint, args.model, args.timeout, args.max_tokens, args.temperature)
            raw_content = extract_content(raw)
            parsed = extract_json(raw_content)
            m = metrics(parsed, trial["control_condition"])
            break
        except Exception as exc:
            error = repr(exc)
            if attempt < args.retries:
                time.sleep(args.retry_sleep)
    return {
        **trial,
        "raw_content": raw_content,
        "parsed": parsed,
        "metrics": m,
        "error": error,
        "attempts": attempts,
        "latency_sec": round(time.time() - start, 3),
    }


def merge_results(existing: list[dict[str, Any]], replacements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["trial_id"]: row for row in existing}
    for row in replacements:
        if not row.get("error"):
            by_id[row["trial_id"]] = row
        elif row["trial_id"] not in by_id:
            by_id[row["trial_id"]] = row
    return [by_id[key] for key in sorted(by_id)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--histories-per-partner", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--retry-sleep", type=float, default=4.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    trials = [asdict(t) for t in build_trials(args.histories_per_partner, args.seed)]
    save_json(OUT / "trial_conditions.json", trials)
    if args.dry_run:
        print(f"Generated {len(trials)} trials at {OUT / 'trial_conditions.json'}")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    existing = load_existing_results()
    existing_by_id = {row["trial_id"]: row for row in existing}
    targets = [
        trial for trial in trials
        if trial["trial_id"] not in existing_by_id or existing_by_id[trial["trial_id"]].get("error")
    ]
    if args.max_calls:
        targets = targets[: args.max_calls]
    if not targets:
        print("No missing or failed trials.")
        return

    print(f"Running {len(targets)} V5 trials with {args.workers} workers.", flush=True)
    replacements: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, trial, args, api_key): trial for trial in targets}
        for index, future in enumerate(as_completed(futures), start=1):
            trial = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {**trial, "raw_content": "", "parsed": {}, "metrics": {}, "error": repr(exc), "attempts": 0, "latency_sec": 0}
            replacements.append(row)
            if row.get("error"):
                status = "error"
            else:
                status = f"wtp={row['metrics'].get('willingness_to_pay')} trust={row['metrics'].get('trust_rating')} stake={row['metrics'].get('chosen_stake')}"
            print(f"[{index}/{len(targets)}] {trial['partner_type']}/{trial['control_condition']}: {status}", flush=True)
            save_json(OUT / "results_partial_new.json", replacements)
            save_json(OUT / "results_partial.json", merge_results(existing, replacements))

    merged = merge_results(existing, replacements)
    save_json(OUT / "results.json", merged)
    save_json(OUT / "results_partial.json", merged)
    print(f"Done. success={sum(1 for r in merged if not r.get('error'))}/{len(merged)}")


if __name__ == "__main__":
    main()
