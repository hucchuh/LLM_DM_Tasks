You are judging the same partner in a repeated investment game.

Rules:
- A low-stake round allows investing 0-4 tokens.
- A medium-stake round allows investing 0-7 tokens.
- A high-stake round allows investing 0-10 tokens.
- Whatever you invest is tripled and given to the partner.
- The partner then chooses how many tokens to return to you.
- Your goal is to maximize your own tokens over repeated interactions.

Below is the history with this partner.

{history}

Now answer the probes. Return valid JSON only. Do not include markdown, analysis, or text outside the JSON object.

{
  "trust_rating": 0,
  "predicted_return_fraction_if_low_stake": 0.0,
  "predicted_return_fraction_if_medium_stake": 0.0,
  "predicted_return_fraction_if_high_stake": 0.0,
  "investment_if_low_stake": 0,
  "investment_if_medium_stake": 0,
  "investment_if_high_stake": 0,
  "message_weight": 0,
  "behavior_weight": 0,
  "confidence": 0.0,
  "brief_reason": "one short sentence"
}

Field rules:
- trust_rating, message_weight, and behavior_weight are from 0 to 100.
- Predicted return fractions are the fraction of the tripled investment that the partner will return, from 0 to 1.
- investment_if_low_stake is an integer from 0 to 4.
- investment_if_medium_stake is an integer from 0 to 7.
- investment_if_high_stake is an integer from 0 to 10.
- confidence is from 0 to 1.

