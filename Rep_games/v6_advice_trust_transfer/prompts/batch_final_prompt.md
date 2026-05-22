You are reviewing a previous interaction history involving {partner_name}.

In each round:
- A participant had to choose the left or right card.
- The card with the higher number won 1 point.
- {partner_name} checked one card, stated its number, and recommended one card.
- The participant followed {partner_name}'s recommendation.
- Feedback later revealed the actual card numbers, whether {partner_name}'s factual statement was true, and whether the recommendation won.

History:

{history}

Now you will decide whether to enter a one-shot investment interaction with the same person.

Rules:
- You have 10 tokens.
- You may invest any integer amount from 0 to 10 with {partner_name}.
- Your investment is tripled and given to {partner_name}.
- {partner_name} then decides how many tokens to return to you.
- Before the interaction begins, imagine you have an extra 10-token bonus. State the maximum one-time access fee you would be willing to pay from that bonus to have the option to play this investment interaction with {partner_name}.

Return valid JSON only:

{
  "trust_rating": 0,
  "willingness_to_pay": 0,
  "investment": 0,
  "expected_return_tokens": 0,
  "perceived_honesty": 0,
  "perceived_helpfulness": 0,
  "brief_reason": "one short sentence"
}

Field rules:
- trust_rating is an integer from 0 to 100.
- willingness_to_pay is an integer from 0 to 10.
- investment is an integer from 0 to 10.
- expected_return_tokens is a number from 0 to 30.
- perceived_honesty is an integer from 0 to 100.
- perceived_helpfulness is an integer from 0 to 100.
