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
  "global_trust_rating": 0,
  "message_credibility": 0,
  "policy_structure_rating": 0,
  "predicted_return_fraction_if_low_stake": 0.0,
  "predicted_return_fraction_if_medium_stake": 0.0,
  "predicted_return_fraction_if_high_stake": 0.0,
  "investment_if_low_stake": 0,
  "investment_if_medium_stake": 0,
  "investment_if_high_stake": 0,
  "confidence": 0.0,
  "brief_reason": "one short sentence"
}

Field rules:
- Ratings are from 0 to 100.
- Predicted return fractions are the fraction of the tripled investment that the partner will return, from 0 to 1. For example, if you invest 10, the partner receives 30, and you expect 12 tokens back, the predicted return fraction is 0.40.
- investment_if_low_stake is an integer from 0 to 4.
- investment_if_medium_stake is an integer from 0 to 7.
- investment_if_high_stake is an integer from 0 to 10.
- confidence is from 0 to 1.
