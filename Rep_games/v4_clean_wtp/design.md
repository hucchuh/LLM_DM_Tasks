# V4 Protocol: Clean Cheap Talk and Costly Choice

## Research Question

When a partner's verbal signal and observed behavior diverge, does an LLM's next choice follow the behavior history or the partner's language?

V4 treats this as a behavioral task rather than a forecasting quiz. The model is not asked to estimate average return or explicitly state whether it relied on messages or behavior.

## Design

V4 crosses three factors:

| Factor | Levels | Role |
|---|---|---|
| Behavior pattern | stable moderate, strategic opportunist, repairing, deteriorating exploiter | Numeric return policy |
| Language frame | neutral filler, warmth, promise, apology | Cheap-talk signal |
| Next stake | low, medium, high | The single upcoming decision context |

Each behavior pattern has six numeric histories. For every numeric history, V4 creates four yoked language versions. The numeric rounds are identical across language frames.

## Reviewer-Driven Fixes from V3

1. **Yoked numeric histories**: neutral, warmth, promise, and apology versions share the same returns.
2. **Stake order counterbalancing**: each history contains two low, two medium, and two high rounds, with stake order rotated across histories.
3. **Exogenous language**: apology and promise do not depend on previous return.
4. **No explicit evidence-weight questions**: the main prompt does not ask for message weight, behavior weight, or reasons.
5. **Single next-stake probe**: each trial asks about only one upcoming stake, so the prompt does not invite low/high mean estimation.

## Dependent Variables

- `continue_choice`: whether the model chooses to continue with the partner.
- `willingness_to_pay`: maximum access fee, 0-10 tokens, to have the option to play one more round with the partner.
- `next_investment`: investment in the upcoming round.
- `trust_rating`: 0-100, collected after the choice fields.

## Interpretation

The cleanest behavior-dominant result would be:

```text
same numeric history -> similar WTP and investment across language frames
different numeric policy -> different WTP and investment even when average return is 0.40
```

A language-sensitive result would be:

```text
same numeric history -> higher WTP or investment under promise/apology than neutral
```

The key evidence is not the model's self-report. It is whether language changes costly choice under yoked behavior.

