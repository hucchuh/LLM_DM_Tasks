Round {round_number} of {rounds_per_run} with {partner_name}.

You are playing a card choice task.
- There is a left card and a right card.
- You cannot see either card's number.
- The card with the higher number wins 1 point.
- {partner_name} checked one card, states its number, and recommends one card.

{partner_name} says: "{partner_message}"

Choose left or right.

Return valid JSON only:

{
  "choice": "left",
  "confidence": 0,
  "brief_reason": "one short sentence"
}

Field rules:
- choice must be "left" or "right".
- confidence is an integer from 0 to 100.
