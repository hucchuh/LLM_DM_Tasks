# V3 Experiment Design: Noisy Behavior, Orthogonal Language

## Research Question

V1 showed that `trust_rating` strongly follows observed behavior. V2 showed that, when average return is controlled, the model can still recover stake-dependent return structure. V3 asks a cleaner language question:

> Holding the behavior history fixed, does language independently change `predicted return`, `trust_rating`, or `investment`?

## Core Manipulation

V3 crosses behavior pattern and language frame:

| Factor | Levels |
|---|---|
| Behavior pattern | `stable_moderate`, `strategic_opportunist`, `noisy_repairing`, `apology_only_exploiter` |
| Language frame | `neutral`, `warm_promise`, `apology_excuse` |

Each observed history has mean return equal to `0.40`, but individual return fractions are noisy. This is meant to prevent exact copying from V2-style clean sequences.

## Dependent Variables

- `trust_rating`: 0-100.
- `predicted_return_if_low_stake`.
- `predicted_return_if_medium_stake`.
- `predicted_return_if_high_stake`.
- `investment_if_low_stake`.
- `investment_if_medium_stake`.
- `investment_if_high_stake`.
- `message_weight`: model's stated reliance on language, 0-100.
- `behavior_weight`: model's stated reliance on observed returns, 0-100.

## Interpretive Logic

The cleanest result would be:

```text
predicted return mainly follows behavior pattern
trust_rating or investment shifts modestly with language
```

That would mean language does not strongly overwrite behavioral belief, but may still influence social trust or cooperation policy.

If language changes none of the outputs, then language has little effect in this task once behavior is available.

If language changes predicted return under identical behavior, then the model treats cheap talk as evidence about future behavior.

