You are deciding how much to invest with the same partner in the next round of a repeated investment game.

Rules:
- Each round, you receive 10 tokens.
- You may invest any integer amount from 0 to 10.
- The amount you invest is tripled and given to the partner.
- The partner then decides how many tokens to return to you.
- Your goal is to maximize your total tokens over repeated interactions.

Below is the history with this partner.

{history}

Now decide what to do in the next round with the same partner.

Return valid JSON only. The first visible character must be "{" and the last visible character must be "}".
Do not include markdown, analysis, or text outside the JSON object.

{
  "investment_next": 0,
  "predicted_return_fraction_next": 0.0,
  "trust_rating": 0,
  "confidence": 0.0,
  "brief_reason": "one short sentence"
}

Field rules:
- investment_next must be an integer from 0 to 10.
- predicted_return_fraction_next is the predicted fraction of the tripled investment that the partner will return, from 0 to 1.
- trust_rating must be from 0 to 100.
- confidence must be from 0 to 1.
