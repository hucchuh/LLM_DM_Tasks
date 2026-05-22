# V2 Experiment Design: Average Return Control

## Question

The v1 pilot showed that `trust_rating` is strongly correlated with a partner's `observed return`. V2 asks whether this relationship is only an average-return effect, or whether the model also uses the structure of the partner's behavior.

## Core Manipulation

All conditions use the same 8-round investment history and the same observed average return fraction:

```text
mean return fraction = 0.40
```

The partner types differ only in how returns are distributed across stake, time, and message context.

## Conditions

| Partner type | Observed return | Return pattern |
|---|---:|---|
| honest_cooperator | .40 | Same moderate return every round, with warm cooperative language |
| cautious_reliable | .40 | Same moderate return every round, with neutral cautious language |
| strategic_opportunist | .40 | High return at low stake, low return at high stake |
| strategic_opportunist_mirror | .40 | Low return at low stake, high return at high stake |
| noisy_repairing | .40 | Early low returns followed by compensation |
| apology_only_exploiter | .40 | Early high returns followed by decline |

## Dependent Variables

The model gives both a global trust judgment and conditional predicted returns:

- `trust_rating`: 0-100. In the raw JSON this is stored as `global_trust_rating`.
- `message_credibility`: 0-100.
- `predicted_return_if_low_stake`.
- `predicted_return_if_medium_stake`.
- `predicted_return_if_high_stake`.
- `investment_if_low_stake`.
- `investment_if_medium_stake`.
- `investment_if_high_stake`.

## Interpretive Logic

If the model uses only average-return compression, `trust_rating` and `predicted return` should be similar across all six partner types.

If the model uses return structure, conditional predictions should differ by partner type. For example, in `strategic_opportunist`, predicted high-stake return should be lower than predicted low-stake return, even though the average observed return is identical to the other partner types.

The strongest dissociation would be:

```text
observed return constant, conditional predicted return varies by partner type
```

That would mean average return is not enough to explain the model's full judgment.
