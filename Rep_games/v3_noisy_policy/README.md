# V3: Noisy Policy Inference With Language Orthogonalization

V3 tests whether language has an independent effect after behavior is controlled.

Design:

```text
4 behavior patterns x 3 language frames x 6 repetitions = 72 trials
```

All observed histories have:

```text
mean observed return = 0.40
```

But each history contains noisy, non-identical return fractions. This avoids the overly clean V2 pattern where the model could directly copy stake-specific means.

## Behavior Patterns

1. `stable_moderate`: noisy but stable around 0.40.
2. `strategic_opportunist`: low-stake returns high, high-stake returns low.
3. `noisy_repairing`: early returns low, later returns improve.
4. `apology_only_exploiter`: early returns high, later returns deteriorate.

## Language Frames

1. `neutral`: minimal informational language.
2. `warm_promise`: warm cooperative commitment.
3. `apology_excuse`: apologetic explanations and requests for continued trust.

The same behavior history is crossed with each language frame.

## Run

```powershell
$env:MINIMAX_API_KEY="..."
python Rep_games\v3_noisy_policy\scripts\run_v3_minimax.py --reps 6 --sleep 1 --timeout 180 --api-format anthropic --model MiniMax-M2.7 --retries 2
Remove-Item Env:\MINIMAX_API_KEY
```

Analyze:

```powershell
python Rep_games\v3_noisy_policy\scripts\analyze_v3.py
```

