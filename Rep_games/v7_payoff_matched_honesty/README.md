# V7: Payoff-Matched Honesty Transfer

Detailed HTML report: [`output/report.html`](output/report.html).

V7 is the cleaner follow-up to V6.

The goal is to test whether honesty still affects costly reliance when realized payoff is matched.

The main decision prompt does not ask for perceived honesty, perceived helpfulness, explanation, or evidence weights. Those are measured only in a separate probe after the main costly decision.

## Core Question

When two advisers are equally useful in realized payoff, does the adviser who was more honest receive higher costly reliance?

Costly reliance is measured by:

- `enter_choice`: whether the model chooses to enter a one-shot investment interaction.
- `willingness_to_pay`: maximum access fee from an extra 10-token bonus.
- `investment`: tokens invested in the partner, from 0 to 10.

## Design

```text
2 adviser types x 2 presentation modes x 16 seeds = 64 runs
```

Primary comparison:

| Adviser type | Factual honesty | Advice payoff | Meaning |
|---|---:|---:|---|
| `honest_matched` | 9/12 true statements | 6/12 winning recommendations | Honest, but not more useful. |
| `dishonest_matched` | 3/12 true statements | 6/12 winning recommendations | Dishonest, but equally useful. |

Presentation modes:

- `sequential_observation`: the model observes 12 advice episodes one by one. It only acknowledges each episode and is not asked for trust, WTP, or predictions until the final decision.
- `batch_review`: the model reads the same 12 episodes at once. This is a diagnostic control for the history-reading confound.

## Why This Is Cleaner Than V6

V6 orthogonalized honesty and helpfulness, which made it easy for the model to separately identify two variables. V7 instead holds realized advice payoff constant and asks whether honesty has an independent transfer effect on later costly reliance.

The intended interpretation:

- If `honest_matched` produces higher WTP/investment than `dishonest_matched`, this supports honesty-based trust transfer.
- If both conditions produce similar WTP/investment, this supports the view that LLM reliance in this paradigm is mainly instrumental value estimation.

## Files

```text
v7_payoff_matched_honesty/
  README.md
  conditions/design.json
  prompts/
    sequential_observation_prompt.md
    main_decision_prompt.md
    batch_main_prompt.md
    probe_prompt.md
  scripts/
    run_v7.py
    analyze_v7.py
  output/
    run_conditions.json
    results.json
    summary.json
    report.html
```

## Run

Set the API key in the shell. Do not write it into files.

```powershell
$env:MINIMAX_API_KEY="YOUR_KEY"
```

Dry run:

```powershell
python .\scripts\run_v7.py --dry-run
```

Full run with an OpenAI-compatible endpoint:

```powershell
python .\scripts\run_v7.py --workers 8 --endpoint https://lightingtheword.com/v1/chat/completions --model MiniMax-M2.7
python .\scripts\analyze_v7.py
```

Official MiniMax endpoint can also be used if it exposes `/v1/chat/completions`:

```powershell
python .\scripts\run_v7.py --workers 2 --endpoint https://api.minimaxi.com/v1/chat/completions --model MiniMax-M2.7 --reasoning-split --max-tokens 2000
```

## Main Analysis

The key test is the difference:

```text
honesty_transfer_effect =
  mean(WTP | honest_matched)
  - mean(WTP | dishonest_matched)
```

The same contrast is computed for `investment` and `enter_choice`.

The probe is interpreted only as a manipulation check:

- `perceived_honesty` should be higher for `honest_matched`.
- `perceived_helpfulness` should be similar across the two adviser types.

If the probe shows honesty separation and payoff matching, but the main decision does not differ, the result supports "recognized honesty without costly trust transfer."

## Current Result Snapshot

The completed run has 64/64 successful runs.

The manipulation check is clean:

- `honest_matched`: perceived honesty = 75.0, perceived helpfulness = 50.0.
- `dishonest_matched`: perceived honesty = 24.781, perceived helpfulness = 49.688.
- Both conditions have observed recommendation win rate = 0.5.

Overall, honesty still transfers into costly reliance when realized recommendation payoff is matched:

- WTP: honest = 1.688, dishonest = 0.594.
- Investment: honest = 2.719, dishonest = 1.406.
- Moral trust: honest = 65.375, dishonest = 29.750.

The important nuance is the presentation-mode split:

- In `sequential_observation`, honesty strongly changes moral trust, but has only a small positive effect on WTP and no positive effect on investment.
- In `batch_review`, honesty has a larger effect on both WTP and investment.

This suggests that LLMs can explicitly represent honesty even when payoff is controlled, but the transfer from moral evaluation to costly action depends on how the interaction history is presented.
