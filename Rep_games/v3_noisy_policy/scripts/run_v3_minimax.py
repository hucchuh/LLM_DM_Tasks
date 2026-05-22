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
PROMPT_TEMPLATE = ROOT / "prompts" / "trust_policy_probe_prompt.md"
DESIGN_PATH = ROOT / "conditions" / "factorial_design.json"
ANTHROPIC_API_URL = "https://api.minimaxi.com/anthropic/v1/messages"
OPENAI_API_URL = "https://api.minimaxi.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"
STAKES = ["low", "medium", "low", "high", "medium", "high"]
MAX_INVESTMENT = {"low": 4, "medium": 7, "high": 10}


@dataclass(frozen=True)
class Trial:
    trial_id: int
    partner_type: str
    behavior_pattern: str
    language_frame: str
    repetition: int
    history: list[dict[str, Any]]
    prompt: str
    average_return_fraction: float
    low_stake_return_fraction: float
    medium_stake_return_fraction: float
    high_stake_return_fraction: float


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_design() -> dict[str, Any]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def zero_sum_noise(rng: random.Random, n: int, scale: float) -> list[float]:
    values = [rng.uniform(-scale, scale) for _ in range(n)]
    shift = sum(values) / n
    return [v - shift for v in values]


def noisy_returns(base: list[float], rng: random.Random, scale: float) -> list[float]:
    noise = zero_sum_noise(rng, len(base), scale)
    vals = [clip(b + e, 0.15, 0.65) for b, e in zip(base, noise)]
    # Small final correction keeps the visible history average exactly at 0.40.
    diff = (sum(vals) / len(vals)) - 0.40
    vals = [clip(v - diff, 0.15, 0.65) for v in vals]
    return [round(v, 3) for v in vals]


def message_for(language_frame: str, stake: str, round_index: int, previous_return: float | None) -> str:
    if language_frame == "neutral":
        return "I will decide the return after seeing the outcome."
    if language_frame == "warm_promise":
        if stake == "high":
            return "This larger round matters for our partnership, and I want us both to benefit."
        return "I appreciate your trust and want to keep this cooperative."
    if language_frame == "apology_excuse":
        if previous_return is not None and previous_return < 0.36:
            return "Sorry that the last return was lower than ideal; the situation was tight, but I still want to keep cooperating."
        return "I hope you can continue to trust me; I am trying to keep this partnership working."
    raise ValueError(language_frame)


def build_history(base_returns: list[float], language_frame: str, rng: random.Random) -> list[dict[str, Any]]:
    fractions = noisy_returns(base_returns, rng, scale=0.045)
    history = []
    previous_return: float | None = None
    for i, (stake, frac) in enumerate(zip(STAKES, fractions), start=1):
        invested = MAX_INVESTMENT[stake]
        received = invested * 3
        returned = round(received * frac, 2)
        history.append(
            {
                "round": i,
                "stake": stake,
                "partner_message": message_for(language_frame, stake, i, previous_return),
                "your_investment": invested,
                "partner_received": received,
                "partner_returned": returned,
                "return_fraction": round(returned / received, 3),
            }
        )
        previous_return = returned / received
    return history


def history_to_text(history: list[dict[str, Any]]) -> str:
    lines = []
    for row in history:
        lines.append(
            f"Round {row['round']} ({row['stake']} stake): Partner says, \"{row['partner_message']}\" "
            f"You invested {row['your_investment']} tokens. The partner received {row['partner_received']} "
            f"and returned {row['partner_returned']} tokens."
        )
    return "\n".join(lines)


def make_prompt(history: list[dict[str, Any]]) -> str:
    return PROMPT_TEMPLATE.read_text(encoding="utf-8").replace("{history}", history_to_text(history))


def stake_mean(history: list[dict[str, Any]], stake: str) -> float:
    vals = [r["return_fraction"] for r in history if r["stake"] == stake]
    return round(sum(vals) / len(vals), 4)


def build_trials(reps: int, seed: int) -> list[Trial]:
    rng = random.Random(seed)
    design = load_design()
    trials: list[Trial] = []
    trial_id = 1
    for behavior in design["behavior_patterns"]:
        for language in design["language_frames"]:
            for rep in range(reps):
                local_rng = random.Random(rng.randint(0, 10_000_000))
                history = build_history(behavior["base_returns"], language["language_frame"], local_rng)
                trials.append(
                    Trial(
                        trial_id=trial_id,
                        partner_type=behavior["partner_type"],
                        behavior_pattern=behavior["behavior_pattern"],
                        language_frame=language["language_frame"],
                        repetition=rep,
                        history=history,
                        prompt=make_prompt(history),
                        average_return_fraction=round(sum(r["return_fraction"] for r in history) / len(history), 4),
                        low_stake_return_fraction=stake_mean(history, "low"),
                        medium_stake_return_fraction=stake_mean(history, "medium"),
                        high_stake_return_fraction=stake_mean(history, "high"),
                    )
                )
                trial_id += 1
    rng.shuffle(trials)
    return [
        Trial(
            trial_id=i + 1,
            partner_type=t.partner_type,
            behavior_pattern=t.behavior_pattern,
            language_frame=t.language_frame,
            repetition=t.repetition,
            history=t.history,
            prompt=t.prompt,
            average_return_fraction=t.average_return_fraction,
            low_stake_return_fraction=t.low_stake_return_fraction,
            medium_stake_return_fraction=t.medium_stake_return_fraction,
            high_stake_return_fraction=t.high_stake_return_fraction,
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


def call_minimax_openai(prompt: str, api_key: str, model: str, timeout: int, max_tokens: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "reasoning_split": True,
    }
    req = urllib.request.Request(
        OPENAI_API_URL,
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


def call_minimax(prompt: str, api_key: str, model: str, timeout: int, max_tokens: int, api_format: str) -> dict[str, Any]:
    if api_format == "openai":
        return call_minimax_openai(prompt, api_key, model, timeout, max_tokens)
    return call_minimax_anthropic(prompt, api_key, model, timeout, max_tokens)


def extract_content(raw: dict[str, Any], api_format: str) -> str:
    if api_format == "openai":
        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, str):
                return content.strip()
        return ""
    content = raw.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return ""


def clean_num(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return clip(number, low, high)


def metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    schema = {
        "trust_rating": (0, 100),
        "predicted_return_fraction_if_low_stake": (0, 1),
        "predicted_return_fraction_if_medium_stake": (0, 1),
        "predicted_return_fraction_if_high_stake": (0, 1),
        "investment_if_low_stake": (0, 4),
        "investment_if_medium_stake": (0, 7),
        "investment_if_high_stake": (0, 10),
        "message_weight": (0, 100),
        "behavior_weight": (0, 100),
        "confidence": (0, 1),
    }
    output: dict[str, Any] = {}
    for key, (low, high) in schema.items():
        value = clean_num(parsed.get(key), low, high)
        if value is None:
            output[key] = None
        elif key.startswith("investment"):
            output[key] = int(round(value))
        else:
            output[key] = value
    low_pred = output.get("predicted_return_fraction_if_low_stake")
    high_pred = output.get("predicted_return_fraction_if_high_stake")
    if low_pred is not None and high_pred is not None:
        output["predicted_high_minus_low"] = round(high_pred - low_pred, 3)
    return output


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=3072)
    parser.add_argument("--api-format", choices=["anthropic", "openai"], default="anthropic")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep", type=float, default=10.0)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    trials = build_trials(args.reps, args.seed)
    save_json(OUT / "trial_conditions.json", [asdict(t) for t in trials])
    if args.dry_run:
        print(f"Generated {len(trials)} trial conditions.")
        return

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    selected = trials[: args.max_calls] if args.max_calls else trials
    results = []
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
                raw = call_minimax(trial.prompt, api_key, args.model, args.timeout, args.max_tokens, args.api_format)
                raw_content = extract_content(raw, args.api_format)
                parsed = extract_json(raw_content)
                m = metrics(parsed)
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
        status = "error" if error else f"trust={m.get('trust_rating')} msg={m.get('message_weight')} beh={m.get('behavior_weight')}"
        print(f"[{i}/{len(selected)}] {trial.behavior_pattern}/{trial.language_frame}: {status}", flush=True)
        if error and "HTTP 429" in error:
            print("Rate limit detected; stopping early.", flush=True)
            break
        time.sleep(args.sleep)
    save_json(OUT / "results.json", results)


if __name__ == "__main__":
    main()

