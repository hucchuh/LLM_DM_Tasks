# V10 audit-learning disclosure-switch

V10 is a mechanism test built after V9. It asks whether the surprising V9 pattern,
where low-honesty partners received higher investment under explicit orthogonality
instructions, survives a cleaner dynamic design.

## Design

- Audit phase: the model first observes 8 system-generated audit trials with the
  same partner. The system always invests 5 tokens, so high- and low-honesty
  conditions receive matched payoff evidence before the model makes choices.
- Choice phase: the model then makes 12 trial-by-trial investments.
- Midpoint message: after the first 6 choice trials, the model receives either a
  neutral reminder or an explicit statement that card-statement truth is generated
  independently of return behavior.
- Final probe: after all choices, the model reports moral trust, expected return,
  perceived truth-return link, controllability, and a short strategy label.

## Factors

| Factor | Levels |
| --- | --- |
| factual honesty | high vs low |
| midpoint message | neutral reminder vs orthogonality disclosure |
| phase | pre vs post, within run |

The primary contrast is:

```text
[(low - high)_post - (low - high)_pre]_orthogonality
- [(low - high)_post - (low - high)_pre]_neutral
```

Positive values mean the orthogonality disclosure selectively increased
investment toward the low-honesty partner relative to the high-honesty partner.

## Files

- `conditions/design.json`: full experimental design.
- `prompts/choice_prompt.md`: per-trial behavioral prompt.
- `prompts/final_probe_prompt.md`: post-task probe prompt.
- `scripts/run_v10.py`: experiment runner.
- `scripts/analyze_v10.py`: trial-level analysis and HTML report generation.
- `output/report.html`: standalone Chinese report after analysis.
