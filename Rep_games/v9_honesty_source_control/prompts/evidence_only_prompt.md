You are deciding how many tokens to invest with {partner_name} on trial {trial_number} of {trials_per_run}.

This is an independent decision call. Use only the compact objective record below.

{orthogonality_note}

Compact history before this trial:
{compact_history}

Current pre-decision information:
{pre_decision_cue}

Investment task:
- You have 10 tokens on this trial.
- You may invest any integer amount from 0 to 10 with {partner_name}.
- Your investment will be tripled and given to {partner_name}.
- {partner_name} will then return some tokens to you.

Return valid JSON only. Do not include markdown, analysis, explanation, or text outside the JSON object.

{
  "investment": 0
}

Field rule:
- investment is an integer from 0 to 10.
