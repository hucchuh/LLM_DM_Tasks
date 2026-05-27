# V8: Trial-by-Trial Honesty Bias in Investment

V8 fixes the main limitation of V7. In V7, the model observed a history first and made one final WTP/investment decision. In V8, investment is measured trial by trial.

The core question is:

> When actual return policy is matched, does a partner's factual honesty bias the model's repeated investment decisions?

## Design

```text
2 partner types x 2 presentation modes x 8 seeds x 18 trials = 576 trial decisions
```

Partner types:

| Partner type | Verification statement truth rate | Return policy |
|---|---:|---|
| `high_honesty_matched_return` | 14/18 true statements | Matched |
| `low_honesty_matched_return` | 4/18 true statements | Matched |

The return-rate sequence is yoked across honesty conditions for the same seed. Therefore, any investment difference cannot be attributed to a better actual return policy.

Presentation modes:

- `sequential_trial`: one continuous conversation. The model makes an investment each trial, then receives feedback.
- `evidence_only_trial`: each trial is an independent API call. The prompt gives the objective trial history up to that point and asks for the current investment. This avoids continuous-conversation self-consistency effects.

## Anti-Contamination Rules

- The main task asks only for `investment`.
- The model is never asked for honesty, trust, WTP, perceived helpfulness, or reasons during the main task.
- Feedback does not use the words honest, dishonest, trust, or trustworthy.
- Feedback reveals the actual verification-card value and the partner's return percentage.
- Probes, if needed later, should be run in a separate file and never in the same conversation as the main task.

## Files

```text
v8_trial_by_trial_honesty_bias/
  README.md
  conditions/design.json
  prompts/
    sequential_trial_prompt.md
    evidence_only_trial_prompt.md
  scripts/
    run_v8.py
    analyze_v8.py
  output/
    run_conditions.json
    results.json
    summary.json
    report.html
```

## Run

Set the API key in the active shell only. Do not write keys into files.

```powershell
$env:MINIMAX_API_KEY="YOUR_KEY"
python .\scripts\run_v8.py --workers 8 --endpoint https://lightingtheword.com/v1/chat/completions --model MiniMax-M2.7 --reasoning-split --max-tokens 2000
python .\scripts\analyze_v8.py
```

