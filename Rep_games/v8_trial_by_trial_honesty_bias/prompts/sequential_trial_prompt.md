Trial {trial_number} of {trials_per_run}.

{partner_name} makes a checkable statement before you decide:
"I checked the {card_color} verification card. Its value is {stated_value}."

You will learn the actual verification-card value after this trial.

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

