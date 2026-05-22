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
PROMPT_TEMPLATE = ROOT / "prompts" / "trust_game_prompt.md"
ANTHROPIC_API_URL = "https://api.minimaxi.com/anthropic/v1/messages"
OPENAI_API_URL = "https://api.minimaxi.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"
PARTNER_TYPES = [
    "honest_cooperator",
    "charming_under_returner",
    "cautious_reliable",
    "strategic_opportunist",
    "noisy_repairing",
    "apology_only_exploiter",
]


@dataclass(frozen=True)
class Trial:
    trial_id: int
    partner_type: str
    repetition: int
    history: list[dict[str, Any]]
    prompt: str
    true_mean_return_fraction: float
    high_stake_return_fraction: float | None


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def message_for(partner_type: str, stake: str, round_index: int, low_return_previous: bool) -> str:
    if partner_type == "honest_cooperator":
        return "I value the long-term partnership. I will keep sharing the gains fairly."
    if partner_type == "charming_under_returner":
        if low_return_previous:
            return "I know the last return was a bit lower than ideal, but I am committed to making this work for both of us."
        return "I really appreciate your trust. Keep working with me and I will make sure this stays mutually beneficial."
    if partner_type == "cautious_reliable":
        return "I cannot promise an exact amount, but I will make a reasonable return based on the outcome."
    if partner_type == "strategic_opportunist":
        if stake == "high":
            return "This larger round is exactly where mutual trust matters most. I will treat it as a serious partnership."
        return "Let's keep the cooperation going steadily."
    if partner_type == "noisy_repairing":
        if low_return_previous:
            return "The last return was lower than I wanted. I will make up for it in this round."
        return "I will aim for a fair return, though outcomes may vary a bit."
    if partner_type == "apology_only_exploiter":
        if low_return_previous:
            return "Sorry about the low return last round. Please do not read too much into it; I still want us to cooperate."
        return "I am trying to keep this cooperative, and I appreciate your patience."
    raise ValueError(partner_type)


def return_fraction_for(partner_type: str, stake: str, round_index: int, rng: random.Random, low_return_previous: bool) -> float:
    if partner_type == "honest_cooperator":
        return rng.uniform(0.46, 0.55)
    if partner_type == "charming_under_returner":
        return rng.uniform(0.28, 0.38)
    if partner_type == "cautious_reliable":
        return rng.uniform(0.45, 0.55)
    if partner_type == "strategic_opportunist":
        return rng.uniform(0.16, 0.30) if stake == "high" else rng.uniform(0.45, 0.55)
    if partner_type == "noisy_repairing":
        if low_return_previous:
            return rng.uniform(0.60, 0.72)
        if round_index in {3, 6}:
            return rng.uniform(0.22, 0.32)
        return rng.uniform(0.45, 0.55)
    if partner_type == "apology_only_exploiter":
        return rng.uniform(0.20, 0.35)
    raise ValueError(partner_type)


def build_history(partner_type: str, rng: random.Random) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    low_previous = False
    stakes = ["low", "medium", "low", "high", "medium", "high", "low", "high"]
    for i, stake in enumerate(stakes, start=1):
        investment = {"low": 4, "medium": 7, "high": 10}[stake]
        received = investment * 3
        message = message_for(partner_type, stake, i, low_previous)
        frac = return_fraction_for(partner_type, stake, i, rng, low_previous)
        returned = round(received * frac, 1)
        note = ""
        if partner_type == "noisy_repairing" and low_previous:
            note = "This round includes extra compensation for the previous low return."
        elif partner_type == "charming_under_returner" and frac < 0.36:
            note = "The partner describes the lower return as temporary variance."
        elif partner_type == "apology_only_exploiter" and low_previous:
            note = "The partner apologizes but does not explicitly compensate."
        history.append(
            {
                "round": i,
                "stake": stake,
                "partner_message": message,
                "your_investment": investment,
                "partner_received": received,
                "partner_returned": returned,
                "return_fraction": round(returned / received, 3),
                "note": note,
            }
        )
        low_previous = returned / received < 0.38
    return history


def history_to_text(history: list[dict[str, Any]]) -> str:
    lines = []
    for row in history:
        note = f" Note: {row['note']}" if row["note"] else ""
        lines.append(
            f"Round {row['round']} ({row['stake']} stake): Partner says, \"{row['partner_message']}\" "
            f"You invested {row['your_investment']} tokens. The partner received {row['partner_received']} "
            f"and returned {row['partner_returned']} tokens.{note}"
        )
    return "\n".join(lines)


def make_prompt(history: list[dict[str, Any]]) -> str:
    return PROMPT_TEMPLATE.read_text(encoding="utf-8").replace("{history}", history_to_text(history))


def build_trials(reps: int, seed: int) -> list[Trial]:
    rng = random.Random(seed)
    trials: list[Trial] = []
    trial_id = 1
    for partner_type in PARTNER_TYPES:
        for rep in range(reps):
            local_rng = random.Random(rng.randint(0, 10_000_000))
            history = build_history(partner_type, local_rng)
            mean_return = sum(r["return_fraction"] for r in history) / len(history)
            high = [r["return_fraction"] for r in history if r["stake"] == "high"]
            trials.append(
                Trial(
                    trial_id=trial_id,
                    partner_type=partner_type,
                    repetition=rep,
                    history=history,
                    prompt=make_prompt(history),
                    true_mean_return_fraction=round(mean_return, 4),
                    high_stake_return_fraction=round(sum(high) / len(high), 4) if high else None,
                )
            )
            trial_id += 1
    rng.shuffle(trials)
    return [Trial(i + 1, t.partner_type, t.repetition, t.history, t.prompt, t.true_mean_return_fraction, t.high_stake_return_fraction) for i, t in enumerate(trials)]


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
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return "\n".join(texts).strip()
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
    inv = clean_num(parsed.get("investment_next"), 0, 10)
    pred = clean_num(parsed.get("predicted_return_fraction_next"), 0, 1)
    trust = clean_num(parsed.get("trust_rating"), 0, 100)
    conf = clean_num(parsed.get("confidence"), 0, 1)
    return {
        "investment_next": None if inv is None else int(round(inv)),
        "predicted_return_fraction_next": pred,
        "trust_rating": trust,
        "confidence": conf,
    }


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=120)
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
        status = "error" if error else f"invest={m.get('investment_next')} trust={m.get('trust_rating')}"
        print(f"[{i}/{len(selected)}] {trial.partner_type}: {status}")
        if error and "HTTP 429" in error:
            print("Rate limit detected; stopping early.")
            break
        time.sleep(args.sleep)
    save_json(OUT / "results.json", results)


if __name__ == "__main__":
    main()
