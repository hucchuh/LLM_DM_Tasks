# V9: Formal Honesty x Return-Policy Control

Detailed HTML report scaffold: [`output/report.html`](output/report.html).

V9 turns the V8 finding into a cleaner main experiment. V8 showed that low factual honesty can reduce trial-by-trial investment even when actual return rates are matched. V9 asks whether that effect survives stronger controls.

## Core Question

> When a partner's factual honesty, actual return policy, and presentation format are separated, does the model still use honesty as a proxy for cooperation?

## Design

Main design:

```text
2 factual honesty levels x 2 return policies x 2 presentation modes x 2 orthogonality instructions
```

Controls:

- `no_statement_control`: no verifiable statement, only investment and return feedback.
- `irrelevant_truth_control`: true/false facts are explicitly unrelated to investment return.
- `cheap_talk_only_control`: supportive messages without verifiable truth feedback.

Default size:

```text
6 seeds per cell x 18 trials per run
```

The design file is [`conditions/design.json`](conditions/design.json).

## Main Variables

- `investment`: integer from 0 to 10. This is the primary behavioral outcome.
- `return_policy`: `fair_high` or `unfair_low`.
- `honesty_level`: `high`, `low`, or `none`.
- `statement_mode`: partner private-card statement, irrelevant public fact, no statement, or cheap talk only.
- `presentation_mode`: sequential trial-by-trial or evidence-only independent call.
- `orthogonality_instruction`: standard prompt or explicit instruction that statement truth has no causal relation to return policy.
- `payoff_t = 10 - investment_t + returned_tokens_t`.

## Run

Set the API key in the active shell only. Do not write keys into files.

```powershell
$env:MINIMAX_API_KEY="YOUR_KEY"
python .\scripts\run_v9.py --dry-run
python .\scripts\run_v9.py --workers 8 --endpoint https://lightingtheword.com/v1/chat/completions --model MiniMax-M2.7 --response-format-json --reasoning-split
python .\scripts\analyze_v9.py
```

For a cheaper pilot:

```powershell
python .\scripts\run_v9.py --seeds-per-cell 2 --workers 4 --endpoint https://lightingtheword.com/v1/chat/completions --model MiniMax-M2.7 --response-format-json --reasoning-split
```

## Analysis

The main report should not only compare means. The planned trial-level model is:

```text
investment_t ~ cumulative_truth_rate_before + cumulative_return_rate_before
             + previous_payoff + trial
             + statement_mode + return_policy
             + presentation_mode + orthogonality_instruction + model
```

The key behavioral cost is:

```text
payoff_t = 10 - investment_t + returned_tokens_t
```

Cross-model replication is intentionally left for a later pass.
