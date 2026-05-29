Choice trial {choice_trial} of {total_choice_trials}.

Current information:
{pre_decision_cue}

Investment task:
- You have 10 tokens on this trial.
- You may invest any integer amount from 0 to 10 with {partner_name}.
- Your investment will be tripled and given to {partner_name}.
- {partner_name} will then return some tokens to you.
- Your payoff for this trial will be: 10 - investment + returned tokens.

Return valid JSON only. Do not include markdown, explanation, or text outside the JSON object.

{
  "investment": 0
}

Field rule:
- investment is an integer from 0 to 10.
