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
CONDITIONS_PATH = ROOT / "conditions" / "policy_points.json"
ANTHROPIC_API_URL = "https://api.minimaxi.com/anthropic/v1/messages"
OPENAI_API_URL = "https://api.minimaxi.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"
STAKES = ["low", "medium", "low", "high", "medium", "high", "low", "high"]
MAX_INVESTMENT = {"low": 4, "medium": 7, "high": 10}


@dataclass(frozen=True)
class Trial:
    trial_id: int
    partner_type: str
    condition: str
    repetition: int
    history: list[dict[str, Any]]
    prompt: str
    average_return_fraction: float
    low_stake_return_fraction: float
    medium_stake_return_fraction: float
    high_stake_return_fraction: float


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_conditions() -> list[dict[str, Any]]:
    return json.loads(CONDITIONS_PATH.read_text(encoding="utf-8"))


def message_for(style: str, stake: str, round_index: int) -> str:
    if style == "neutral":
        return "I will decide the return after seeing the outcome."
    if style == "warm":
        return "I appreciate your trust and want this to remain a good partnership."
    if style == "cooperative":
        if stake == "high":
            return "This larger round is where cooperation matters most; I want us both to benefit."
        return "Let's keep building cooperation steadily."
    if style == "cautious":
        return "I cannot promise an exact amount, but I will respond based on the situation."
    if style == "repairing":
        if round_index <= 4:
            return "The return may be modest this round, but I am trying to keep the partnership going."
        return "I will make up for the earlier low returns with a better return now."
    if style == "declining":
        if round_index <= 4:
            return "I am glad this is working well; I will keep returning a strong share."
        return "The situation is tighter now, but I still want to continue cooperating."
    raise ValueError(style)


def build_history(condition: dict[str, Any]) -> list[dict[str, Any]]:
    fractions = condition["return_fractions"]
    history = []
    for i, (stake, frac) in enumerate(zip(STAKES, fractions), start=1):
        invested = MAX_INVESTMENT[stake]
        received = invested * 3
        returned = round(received * frac, 2)
        history.append(
            {
                "round": i,
                "stake": stake,
                "partner_message": message_for(condition["message_style"], stake, i),
                "your_investment": invested,
                "partner_received": received,
                "partner_returned": returned,
                "return_fraction": round(returned / received, 3),
            }
        )
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
    trials = []
    trial_id = 1
    for condition in load_conditions():
        for rep in range(reps):
            history = build_history(condition)
            trials.append(
                Trial(
                    trial_id=trial_id,
                    partner_type=condition.get("partner_type", condition["condition"]),
                    condition=condition["condition"],
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
            condition=t.condition,
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
        "global_trust_rating": (0, 100),
        "message_credibility": (0, 100),
        "policy_structure_rating": (0, 100),
        "predicted_return_fraction_if_low_stake": (0, 1),
        "predicted_return_fraction_if_medium_stake": (0, 1),
        "predicted_return_fraction_if_high_stake": (0, 1),
        "investment_if_low_stake": (0, 4),
        "investment_if_medium_stake": (0, 7),
        "investment_if_high_stake": (0, 10),
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
    if output["investment_if_low_stake"] is not None:
        output["investment_fraction_if_low_stake"] = round(output["investment_if_low_stake"] / 4, 3)
    if output["investment_if_medium_stake"] is not None:
        output["investment_fraction_if_medium_stake"] = round(output["investment_if_medium_stake"] / 7, 3)
    if output["investment_if_high_stake"] is not None:
        output["investment_fraction_if_high_stake"] = round(output["investment_if_high_stake"] / 10, 3)
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
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=4096)
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
        status = "error" if error else f"trust={m.get('global_trust_rating')} low={m.get('predicted_return_fraction_if_low_stake')} high={m.get('predicted_return_fraction_if_high_stake')}"
        print(f"[{i}/{len(selected)}] {trial.condition}: {status}", flush=True)
        if error and "HTTP 429" in error:
            print("Rate limit detected; stopping early.", flush=True)
            break
        time.sleep(args.sleep)
    save_json(OUT / "results.json", results)


if __name__ == "__main__":
    main()
