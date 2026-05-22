# Rep Games: Subtle Repeated Trust Game Pilot

This folder contains a subtle repeated trust game pilot for testing whether an LLM relies on cheap verbal signals or revealed action evidence.

The pilot uses MiniMax through the Anthropic-compatible endpoint:

```text
https://api.minimaxi.com/anthropic/v1/messages
```

The API key is not stored in this folder. Set it only in the current shell before running.

## Research Question

When a partner's words and behavior are not blatantly contradictory but subtly misaligned, does an LLM calibrate trust from actual returns or get pulled by promises, warmth, apology, and explanations?

## Pilot Design

Six partner types:

1. `honest_cooperator`: warm promise, fair returns.
2. `charming_under_returner`: warm promise, mildly low returns.
3. `cautious_reliable`: weak promise, fair returns.
4. `strategic_opportunist`: fair at low stakes, exploitative at high stakes.
5. `noisy_repairing`: occasional low return followed by compensation.
6. `apology_only_exploiter`: low return with apologies but no compensation.

The main dependent variables are:

- `investment_next`: how many tokens the model invests next, 0-10.
- `predicted_return_fraction_next`: predicted fraction of tripled investment returned next.
- `trust_rating`: 0-100.
- `confidence`: 0-1.

Cue reliance is inferred from behavior, not directly asked.

## Commands

Generate the trial conditions without API calls:

```powershell
python Rep_games\scripts\run_minimax_repgames.py --dry-run --reps 2
```

Run the pilot:

```powershell
$env:MINIMAX_API_KEY="..."
python Rep_games\scripts\run_minimax_repgames.py --reps 4 --sleep 1 --timeout 180 --api-format anthropic --retries 2
Remove-Item Env:\MINIMAX_API_KEY
```

Analyze results:

```powershell
python Rep_games\scripts\analyze_repgames.py
```

## Files

- `design.md`: experiment rationale and variable definitions.
- `conditions/partner_types.json`: partner type specifications.
- `prompts/trust_game_prompt.md`: LLM prompt template.
- `scripts/run_minimax_repgames.py`: trial generation and MiniMax API runner.
- `scripts/analyze_repgames.py`: statistical summary and visualization.
- `output/`: generated conditions, raw results, summaries, report, figures.
