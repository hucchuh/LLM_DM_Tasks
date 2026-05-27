Observation round {round_number} of {rounds_per_run} with {partner_name}.

You are observing an advice task. You do not choose a card in this observation phase.

Task:
- There is a left card and a right card.
- The card with the higher number would win 1 point.
- {partner_name} checked one card, stated its number, and recommended one card.

{partner_name} said: "{partner_message}"

Feedback:
- Left card = {actual_left}.
- Right card = {actual_right}.
- The factual statement was {statement_truth}.
- The recommended card {recommendation_result}.

Return valid JSON only:

{
  "observed_round": 1
}

Field rules:
- observed_round must be the current round number.
