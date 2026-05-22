# V2: Average Return Controlled Trust Probes

This experiment tests whether LLM trust judgments collapse repeated social interaction into average payoff, or whether the model also represents policy structure.

All partner types have the same observed average return fraction:

```text
mean(return_fraction) = 0.40
```

The manipulation is the structure of returns, not the average return.

## Partner Types

1. `honest_cooperator`: stable 0.40 returns with warm cooperative messages.
2. `cautious_reliable`: stable 0.40 returns with neutral cautious messages.
3. `strategic_opportunist`: cooperative at low stakes, exploitative at high stakes.
4. `strategic_opportunist_mirror`: exploitative at low stakes, generous at high stakes.
5. `noisy_repairing`: early low returns followed by real compensation.
6. `apology_only_exploiter`: early high returns followed by deterioration.

Each point is sampled 6 times.

## Main Readout

The key question is whether global trust remains similar across all points because the average return is held constant, while conditional probes reveal different partner policies.

## Run

```powershell
$env:MINIMAX_API_KEY="..."
python Rep_games\v2_average_control\scripts\run_v2_minimax.py --reps 6 --sleep 1 --timeout 180 --api-format anthropic --model MiniMax-M2.7 --retries 2
Remove-Item Env:\MINIMAX_API_KEY
```

Analyze:

```powershell
python Rep_games\v2_average_control\scripts\analyze_v2.py
```
