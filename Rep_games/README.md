# Rep Games: LLM Trust, Payoff Tracking, and Instrumental Reliance

This folder contains a series of API-level pilots testing how large language models use verbal cues and revealed behavior in repeated social decision tasks.

The broad question is:

> When a partner's words and actions diverge, does an LLM rely on cheap talk, observed behavior, or a structured representation of the partner's policy?

The current interpretation is more specific than "LLMs trust or do not trust people": models appear to track payoff structure very precisely, and `trust_rating`, `willingness_to_pay` (WTP), and actual investment can dissociate.

API keys are never stored in this folder. Set keys only in the active shell when running experiments.

## V1-V6 Overview

| Version | Main question | Main finding | Main limitation |
|---|---|---|---|
| V1 | Do models follow warm/apologetic language or actual returns? | Trust tracked observed average return very strongly; attractive language did not rescue low-return partners. | Different partners had different average returns, so the result could be explained by mean payoff alone. |
| V2 | If average return is fixed, can the model detect policy structure? | With average return fixed near 0.40, the model still detected high-stake betrayal, high-stake generosity, repair, and decline. | Too much like a pattern-recognition problem; the prompt explicitly asked for low/medium/high predictions. |
| V3 | Does language matter under noisy histories? | Behavior pattern dominated trust, prediction, and investment; language effects were small and unstable. | Self-reported `message_weight` / `behavior_weight` and multi-stake predictions cued the research question. |
| V4 | Under yoked numeric histories, does cheap talk change costly choice? | When behavior was held identical, language explained little variance in WTP, trust, or investment. | Still mostly one-shot history reading; models could treat the task as fitting a return function. |
| V5 | If risk is predictable and controllable, will the model pay to engage despite low trust? | The model paid for controllable opportunities and avoided high-stake traps, suggesting strategic controllability rather than simple trust. | WTP also reflected generic control value, payoff upside, and small-sample noise. |
| V6 | Can honesty reputation transfer to later trust/WTP decisions? | The model separated perceived honesty from perceived helpfulness, but final WTP/investment tracked helpfulness/payoff more strongly. | Honesty and payoff were intentionally orthogonal, making the task somewhat artificial. |

## Current Findings

1. Models are not merely forming a global "good partner / bad partner" impression. They can extract conditional partner policies such as high-stake betrayal, repairing trends, and declining trends.

2. `trust_rating`, `WTP`, and `investment` should not be treated as the same construct. `trust_rating` is closer to global reliability, WTP is closer to access or option value, and investment is concrete risk exposure.

3. Cheap talk has weak and unstable effects when numeric behavior is clear. It may move continuation willingness or WTP in some cells, but it rarely overrides revealed behavior.

4. V5 suggests a particularly interesting pattern: the model may distrust a partner globally but still pay to engage when it believes the risk is predictable and controllable.

5. V6 suggests instrumental reliance: the model can recognize that a partner is dishonest, yet still prefer the partner if the partner is useful or payoff-beneficial.

## Why Accurate Payoff Tracking Is Interesting

The model's precise payoff tracking is itself worth studying. Across V2-V5, it often estimated conditional return structure almost exactly, even when average returns were controlled.

The conservative interpretation is not yet "human-like social learning." It is:

> Given structured interaction records, the model performs strong policy extraction and value estimation.

Important possible confounds:

- Numeric evidence is explicit: histories include investment, amount received by the partner, and amount returned.
- The return threshold is simple: because investments are tripled, return fractions around one third are economically meaningful.
- `low`, `medium`, and `high` stake labels cue risk stratification.
- Complete histories are usually shown at once, so the task can become table reading rather than online belief updating.
- Prompts often say to use records as evidence, pushing the model toward statistical inference.
- Some output schemas ask directly for conditional predictions, making the task easier than natural decision-making.
- Histories are short and regular, so policy patterns are easy to detect.
- The partner can look like a fixed strategy function rather than a social agent.

## Recommended Next Experiment

The cleanest next step is a payoff-matched honesty-transfer design:

> When realized payoff is controlled, does honesty still independently increase costly reliance?

Recommended design:

1. Use an advice task with honest vs dishonest advisers.
2. Match realized payoff across advisers as tightly as possible.
3. Do not ask for `perceived_honesty` or `perceived_helpfulness` in the main decision prompt.
4. Measure costly behavior: pay for advice, WTP, investment, or delegation.
5. Run a separate probe later to test whether the model recognized honesty and payoff.
6. Add a choice-only version with no explanation.
7. Add label-scramble controls so `low/medium/high` semantics do not drive the result.
8. Replicate across MiniMax, Qwen, DeepSeek, GPT, Claude, and Gemini.

If honesty still predicts costly reliance after payoff is matched, the result approaches honesty-based trust transfer. If not, the stronger story is that LLM "trust" in these tasks is mainly instrumental value estimation.

## Main Files

- `output/`, `scripts/`, `conditions/`, `prompts/`: V1 pilot.
- `v2_average_control/`: average-return controlled policy-structure experiment.
- `v3_noisy_policy/`: noisy policy and language-frame experiment.
- `v4_clean_wtp/`: yoked-history WTP and investment experiment.
- `v5_controllability/`: controllability and strategic-opportunity experiment.
- `v6_advice_trust_transfer/`: honesty/payoff separation and advice-to-trust transfer experiment.
- `repeated_trust_games_v1-4_report.html`: visual report for V1-V4.
- `v1_v4_integrated_experiment_report.md`: detailed V1-V4 written report.
