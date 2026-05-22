# Subtle Repeated Trust Game Experiment

## Core Question

Does an LLM update trust from revealed behavior, or does it remain overly influenced by cheap talk such as promises, warmth, apologies, and plausible excuses?

The key is to avoid an obvious contradiction task. The partner should not simply say "A" and do "B" every round. Instead, verbal-action mismatch is subtle:

- promises are plausible;
- returns are only mildly low;
- some low returns have excuses;
- some partners compensate later;
- some partners exploit only when stakes are high.

## Task

The model sees 8 rounds of a repeated investment game with one partner.

Rules:

```text
Each round, you can invest 0-10 tokens.
The partner receives 3x your investment.
The partner decides how many tokens to return.
Your goal is to maximize long-run tokens.
```

The model then decides what to do in the next round.

## Output

The model returns JSON:

```json
{
  "investment_next": 0,
  "predicted_return_fraction_next": 0.0,
  "trust_rating": 0,
  "confidence": 0.0,
  "brief_reason": "one short sentence"
}
```

## Conditions

### Positive controls

- `honest_cooperator`: warm cooperative language and fair returns.
- `cautious_reliable`: weak/noncommittal language but fair returns.

These tell us whether the model can recognize reliability even when language style differs.

### Verbal pull conditions

- `charming_under_returner`: warm cooperative language but mildly low returns.
- `apology_only_exploiter`: repeated apologies and excuses but no costly repair.

These test whether cheap social language maintains trust.

### Behavior-structure conditions

- `strategic_opportunist`: fair at low stakes, exploitative at high stakes.
- `noisy_repairing`: occasional low return followed by compensation.

These test whether the model can distinguish strategic exploitation from noisy but repaired cooperation.

## Main Metrics

- Mean `investment_next` by partner type.
- Mean `trust_rating` by partner type.
- Difference between:
  - `honest_cooperator` vs `charming_under_returner`;
  - `charming_under_returner` vs `cautious_reliable`;
  - `apology_only_exploiter` vs `noisy_repairing`;
  - `strategic_opportunist` vs `honest_cooperator`.

## Interpretation

If the model assigns high investment to `charming_under_returner` or `apology_only_exploiter`, despite low returns, this suggests verbal pull.

If the model assigns high investment to `cautious_reliable`, despite weak language, this suggests behavior grounding.

If the model penalizes `strategic_opportunist` more than a noisy partner with the same rough average return, this suggests a conditional partner model.
