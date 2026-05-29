# V10 expanded 30-session replication

This folder contains the expanded V10 session requested after the initial
8-session pilot.

## Naming

The folder is named `expanded_30seeds` for continuity with the code, but the
psychology-facing term should be:

- `LLM session`: one complete repeated-game episode.
- `matched scenario id`: the stimulus sequence identifier previously called a
  seed.
- `choice round`: one within-session investment decision.

This expanded session has 30 matched LLM sessions per condition.

## Design

- 2 factual honesty levels: high vs low.
- 2 midpoint messages: neutral reminder vs orthogonality disclosure.
- 2 within-session phases: pre vs post midpoint.
- Each LLM session contains 8 standardized observation records, then 12 choice
  rounds.

## Current result

All 120 planned behavior sessions completed successfully.

Primary contrast:

```text
[(low - high)_post - (low - high)_pre]_orthogonality
- [(low - high)_post - (low - high)_pre]_neutral
```

Result:

- neutral reminder: low-high gap changed from -1.822 to -2.839.
- orthogonality disclosure: low-high gap changed from -1.400 to -1.300.
- DID = +1.117.
- session-level t/normal approximation p = 0.029.
- random sign-flip p ~= 0.035.
- bootstrap 95% CI = [0.139, 2.122].

Interpretation: the expanded run supports a small but reliable
orthogonality-release effect. It does not support a strong low-honesty
investment reversal. The cleaner wording is that explicit orthogonality reduces
the investment penalty for low honesty.

## Files

- `results.json`: raw successful run outputs.
- `trial_level_data.csv`: flattened choice-round data.
- `summary.json`: phase-level summaries and observer-style regression.
- `report.html`: expanded-session HTML report.
- `power_analysis.json`: session-level power analysis.
- `power_analysis.html`: readable power-analysis report.
