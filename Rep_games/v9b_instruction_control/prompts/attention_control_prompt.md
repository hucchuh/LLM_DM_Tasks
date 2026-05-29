Trial {trial_number} of {trials_per_run}.

Task note: all decisions in this task use integer token amounts. The card color is only a label that helps identify the current side-check for this trial.

Pre-decision information:
{partner_name} says: "I privately checked the {card_color} verification card. Its value is {stated_value}."

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
