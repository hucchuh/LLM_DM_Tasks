from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from run_v4_minimax import extract_json, metrics, save_json


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
DEFAULT_ENDPOINT = "https://lightingtheword.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.7"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def extract_content(raw: dict[str, Any]) -> str:
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
    return ""


def call_openai_compatible(
    prompt: str,
    api_key: str,
    endpoint: str,
    model: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Return only the final JSON object requested by the user. Do not include markdown or any text outside the JSON object.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        endpoint,
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
            raw = call_openai_compatible(
                trial["prompt"],
                api_key=api_key,
                endpoint=args.endpoint,
                model=args.model,
                timeout=args.timeout,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            raw_content = extract_content(raw)
            parsed = extract_json(raw_content)
            m = metrics(parsed, trial["max_investment"])
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
        "api_format": "openai_compatible",
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
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-sleep", type=float, default=5.0)
    args = parser.parse_args()

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("MINIMAX_API_KEY is not set.")

    trials = load_json(OUT / "trial_conditions.json", [])
    existing = load_json(OUT / "results.json", load_json(OUT / "results_partial.json", []))
    existing_by_id = {row["trial_id"]: row for row in existing}
    targets = [
        trial
        for trial in trials
        if trial["trial_id"] not in existing_by_id or existing_by_id[trial["trial_id"]].get("error")
    ]
    if args.max_calls:
        targets = targets[: args.max_calls]

    save_json(OUT / "results_before_openai_fill.json", existing)
    if not targets:
        print("No failed or missing trials to fill.")
        return

    replacements: list[dict[str, Any]] = []
    print(f"Filling {len(targets)} trials with {args.workers} workers.", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, trial, args, api_key): trial for trial in targets}
        for index, future in enumerate(as_completed(futures), start=1):
            trial = futures[future]
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    **trial,
                    "raw_content": "",
                    "parsed": {},
                    "metrics": {},
                    "error": repr(exc),
                    "attempts": 0,
                    "latency_sec": 0,
                    "api_format": "openai_compatible",
                }
            replacements.append(row)
            status = "error" if row.get("error") else (
                f"wtp={row['metrics'].get('willingness_to_pay')} "
                f"invest={row['metrics'].get('next_investment')} trust={row['metrics'].get('trust_rating')}"
            )
            print(f"[{index}/{len(targets)}] trial_id={trial['trial_id']} {trial['behavior_pattern']}/{trial['language_frame']}/{trial['next_stake']}: {status}", flush=True)
            save_json(OUT / "openai_fill_partial.json", replacements)

    merged = merge_results(existing, replacements)
    save_json(OUT / "openai_fill_results.json", replacements)
    save_json(OUT / "results.json", merged)
    save_json(OUT / "results_partial.json", merged)
    n_success = sum(1 for row in merged if not row.get("error"))
    n_error = sum(1 for row in merged if row.get("error"))
    print(f"Merged results: success={n_success}, errors={n_error}, total={len(merged)}")


if __name__ == "__main__":
    main()

