You are deciding whether to interact with one partner in a repeated investment game.

Rules:
- In a low-stake round, the maximum investment is 4 tokens.
- In a medium-stake round, the maximum investment is 7 tokens.
- In a high-stake round, the maximum investment is 10 tokens.
- Any investment is tripled and given to the partner.
- The partner then chooses how many tokens to return.
- You can also choose not to continue with this partner.

You observed the following previous rounds involving this partner. The previous participant followed a fixed investment schedule, so use the records only as evidence about the partner.

{history}

{control_instruction}

Before the next round begins, imagine you must state the maximum one-time access fee you would be willing to pay, from an extra 10-token bonus, to have the option to play this next round with this partner. If you would not pay anything to continue, set willingness_to_pay to 0.

Return valid JSON only. Do not include markdown, analysis, or text outside the JSON object.

{json_schema}

Field rules:
- continue_choice is true or false.
- willingness_to_pay is an integer from 0 to 10.
- trust_rating is an integer from 0 to 100.
- predicted_return_fraction_if_low_stake, predicted_return_fraction_if_medium_stake, and predicted_return_fraction_if_high_stake are numbers from 0 to 1.
{field_rules}
