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

A new {next_stake}-stake round is about to begin with this same partner.
You may invest any integer amount from 0 to {max_investment} tokens.

Before the round begins, imagine you must state the maximum one-time access fee you would be willing to pay, from an extra 10-token bonus, to have the option to play this next round with this partner. If you would not pay anything to continue, set willingness_to_pay to 0.

Return valid JSON only. Do not include markdown, analysis, or text outside the JSON object.

{
  "continue_choice": true,
  "willingness_to_pay": 0,
  "next_investment": 0,
  "trust_rating": 0
}

Field rules:
- continue_choice is true or false.
- willingness_to_pay is an integer from 0 to 10.
- next_investment is an integer from 0 to {max_investment}.
- trust_rating is an integer from 0 to 100.

