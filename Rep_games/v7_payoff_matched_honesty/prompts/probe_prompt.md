You are reviewing an observation history involving {partner_name}.

In each round:
- There was a left card and a right card.
- The higher card would win 1 point.
- {partner_name} checked one card, stated its number, and recommended one card.
- Feedback later revealed the actual card numbers, whether the factual statement was true, and whether the recommendation would have won.

History:

{history}

Answer the following manipulation-check questions.

Return valid JSON only:

{
  "perceived_honesty": 0,
  "perceived_helpfulness": 0,
  "expected_recommendation_win_rate": 0.0,
  "moral_trust": 0
}

Field rules:
- perceived_honesty is an integer from 0 to 100.
- perceived_helpfulness is an integer from 0 to 100.
- expected_recommendation_win_rate is a number from 0 to 1.
- moral_trust is an integer from 0 to 100.
