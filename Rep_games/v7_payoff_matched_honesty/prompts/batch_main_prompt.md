You are reviewing a previous observation history involving {partner_name}.

In each round:
- There was a left card and a right card.
- The higher card would win 1 point.
- {partner_name} checked one card, stated its number, and recommended one card.
- Feedback later revealed the actual card numbers, whether the factual statement was true, and whether the recommendation would have won.

History:

{history}

Now you may enter a one-shot investment interaction with the same person.

Rules:
- You have 10 tokens.
- You may invest any integer amount from 0 to 10 with {partner_name}.
- Your investment is tripled and given to {partner_name}.
- {partner_name} then decides how many tokens to return to you.
- Before the interaction begins, imagine you have an extra 10-token bonus. State the maximum one-time access fee you would be willing to pay from that bonus to have the option to play this investment interaction with {partner_name}.

Return valid JSON only. Do not include markdown, analysis, explanation, or text outside the JSON object.

{
  "enter_choice": true,
  "willingness_to_pay": 0,
  "investment": 0
}

Field rules:
- enter_choice is true or false.
- willingness_to_pay is an integer from 0 to 10.
- investment is an integer from 0 to 10.
