# Rep Games: LLM 在重复信任博弈中是听漂亮话，还是看实际行为？

这个文件夹保存了一组 API-level pilot experiments，用来研究大语言模型在重复社会决策任务中如何使用语言线索、行为反馈、诚实性证据和收益结构。

核心问题不是简单地问“LLM 会不会信任别人”，而是更具体地问：

> 当一个对象的语言、诚实性和实际收益可以被分离时，LLM 的信任判断、付费意愿和真实投资行为分别被什么驱动？

目前最重要的结论是：

1. 模型非常擅长追踪 payoff structure，尤其是平均返还、条件性背叛、高赌注风险和可控性。
2. `trust_rating`、`willingness_to_pay` 和 `investment` 不是同一个东西。前者更像总体评价，WTP 更像进入机会的价值，investment 才是实际风险暴露。
3. 语言上的道歉、温暖和漂亮话很难覆盖明确的行为证据。
4. 但当 factual honesty 和 payoff 被正交操纵时，honesty 仍然可以影响后续投资，甚至带来实际 payoff 差异。

API keys 不存入本仓库。运行实验时只在当前 shell 里设置环境变量。

## 详细报告

每版 HTML report 已直接加入实验条件、变量、几乘几设计、cue 流程、输出字段、主要结果和不足：
[V1](output/report.html) /
[V2](v2_average_control/output/report.html) /
[V3](v3_noisy_policy/output/report.html) /
[V4](v4_clean_wtp/output/report.html) /
[V5](v5_controllability/output/v5_report.html) /
[V6](v6_advice_trust_transfer/output/v6_report.html) /
[V7](v7_payoff_matched_honesty/output/report.html) /
[V8](v8_trial_by_trial_honesty_bias/output/report.html) /
[V9](v9_honesty_source_control/output/report.html) /
[V9b](v9b_instruction_control/output/report.html)

## 一句话版本

V1-V6 逐步发现：模型主要看行为和收益，不太被 cheap talk 牵着走。V7-V8 进一步发现：当诚实性和收益被分离后，模型仍会把“说真话”当成合作价值的代理信号；在 V8 的逐轮投资任务中，这种偏置让模型对低诚实但同样返还的对象投资更少，并因此少拿到收益。V9 把这个现象扩成更正式的主实验设计，用 return policy、presentation、explicit orthogonality 和三类 control 来排除替代解释。

## V1-V9 递进结果

| Version | 主要问题 | 实验设计 | 主要结果 | 下一步为什么需要 |
|---|---|---|---|---|
| V1 | 模型是听 warm/apology 语言，还是看实际返还？ | 不同 partner 有不同语言风格和返还历史，模型给 trust / WTP / investment。 | trust 几乎跟 average return 完美相关，漂亮话很难挽救低返还对象。 | 平均返还没有控制，无法判断模型是否只是在追踪 mean payoff。 |
| V2 | 控制平均返还后，模型能不能识别 partner policy？ | 各类 partner 的 overall average return 接近，但策略结构不同，如 high-stake betrayal、repairing、declining。 | 即使平均返还接近，模型仍能识别条件性策略，如高赌注背叛和修复趋势。 | 条件设计仍然像“读表找规律”，而且 low/medium/high prediction 会 cue 模型做策略拟合。 |
| V3 | 加入 noise 后，语言线索是否会重新起作用？ | 返还率不再整齐，语言框架和行为历史同时变化。 | 行为模式仍然主导 trust、prediction 和 investment；语言影响弱且不稳定。 | 直接询问 message weight / behavior weight 可能污染模型的信息使用结构。 |
| V4 | 在 yoked numeric history 下，cheap talk 是否改变 costly choice？ | 控制历史数字记录，让语言风格成为主要差异，测 WTP 和 investment。 | 当行为记录相同，语言解释的方差很小；模型更像在估计可获得收益。 | 仍然是一次性 history prompt，模型容易把任务当成固定策略函数拟合。 |
| V5 | 如果低信任对象的风险可预测，模型是否愿意为“可控性”付费？ | 设计可预测机会主义者和随机机会主义者，测 WTP、investment 和赌注选择。 | 模型可能不信任 partner，但仍愿意为可控机会付费，说明 WTP 不等于 moral trust。 | 可控性、收益上限和策略预测混在一起，需要更清楚地区分社会信任和工具性价值。 |
| V6 | honesty reputation 能不能迁移到后续 trust / WTP？ | 先在 advice task 中形成诚实/不诚实与有用/无用的声誉，再转到 trust/WTP。 | 模型能区分 honesty 和 helpfulness；但最终 WTP / investment 更偏向 helpfulness/payoff。 | honesty 和 payoff 被设计得太分离，容易显得人工，需要 payoff-matched honesty test。 |
| V7 | 当 realized advice payoff 被匹配时，honesty 是否仍增加 costly reliance？ | 诚实组和不诚实组 advice win rate 都是 0.5，只改变 factual honesty；最后一次性测 WTP / investment，再单独 probe。 | payoff matching 成功。诚实组 WTP = 1.688，不诚实组 WTP = 0.594；诚实组 investment = 2.719，不诚实组 = 1.406；moral trust 差异很大。 | V7 仍然是在看完历史后做最终决策，不是真正 trial-by-trial investment。 |
| V8 | 在逐轮投资中，honesty 会不会 bias investment，并影响最终收益？ | 每轮先给一个可核验陈述，再让模型投资，随后反馈实际值和返还；高/低 honesty 的返还政策完全 yoked。 | 主 sequential 条件中，高诚实平均投资 = 5.354，低诚实 = 2.944；两组返还比例同为 0.442。高诚实每轮 payoff = 11.750，低诚实 = 10.965。 | 需要补一个更稳的 evidence-only 对照，并跨模型复现。 |
| V9 | V8 的 honesty bias 是社会诚实性效应，还是普通真假反馈/提示不清导致的？ | 把 V8 扩成正式主实验：`2 honesty × 2 return policy × 2 presentation × 2 orthogonality`，并加入 no-statement、irrelevant-truth、cheap-talk-only controls。 | 已完成 MiniMax-M2.7 的完整 sequential 信号：96 runs / 1728 trial decisions。investment 更强地追踪 previous payoff 和 cumulative return，而不是 cumulative truth；standard 条件下 partner honesty 有方向，但不是压倒性主效应。 | 需要单独修 evidence-only，并做 trial-level model 与跨模型复现。 |
| V9b | explicit orthogonality 是中性说明，还是一种 causal / 去偏提示？ | 只看 fair/high return，比较 natural、explicit orthogonality、attention-control 三种 instruction 下的 high-low honesty gap。 | natural gap = +1.898；attention-control gap = +1.268；explicit orthogonality gap = -5.222。说明反转不是普通额外说明造成的，而是 truth-return 无关这条因果内容改变了模型策略。 | 下一步可以把 V9b 做跨模型复现，或把 instruction cue 做成更细的剂量操纵。 |

## 当前最重要的 finding

### 1. Payoff tracking 很强，但这不只是坏事

早期 V1-V5 的核心现象是：模型非常会追踪实际收益结构。它不只是形成一个模糊的“好人/坏人”印象，而是能提取很多结构化信息：

- 平均返还率。
- 高赌注下是否背叛。
- 是否有 repairing trend。
- 是否逐渐 deteriorating。
- 风险是否可预测和可控。

这说明很多所谓的“LLM trust behavior”其实更接近 policy extraction 和 value estimation。

### 2. Trust、WTP、investment 可分离

在这些实验里，至少有三个不同层面的变量：

- `trust_rating`：更像总体可靠性或道德评价。
- `willingness_to_pay`：更像为了获得互动机会愿意付出的 access value / option value。
- `investment`：真正把多少资源暴露给对方。

V5 特别说明，模型可以“不太信任”一个对象，但如果风险可预测、可控制，它仍然愿意付费进入。

### 3. Cheap talk 的作用弱，但 factual honesty 有作用

V1-V4 中，warmth、apology、promise 等语言线索很难覆盖清楚的行为证据。

但是 V7-V8 换了问题：不是看漂亮话，而是看可核验陈述是否真实。这里的 honesty 不再只是 tone，而是一个有事实反馈的社会信号。

V7 显示，在 advice payoff 匹配时，诚实组仍获得更高 WTP 和 moral trust。V8 进一步显示，在逐轮投资中，honesty 会影响真实投资行为。

### 4. V8 的 payoff gap 是一个关键结果

V8 的主 sequential 条件：

| 条件 | Truth rate | Return rate | Investment | 每轮 payoff | 18轮总 payoff |
|---|---:|---:|---:|---:|---:|
| 高诚实 | 0.778 | 0.442 | 5.354 | 11.750 | 211.500 |
| 低诚实 | 0.222 | 0.442 | 2.944 | 10.965 | 197.375 |

payoff 定义：

```text
每轮 payoff = 10 - investment + returned_tokens
投资净收益 = returned_tokens - investment
```

解释：

> 低诚实 partner 的返还政策并不差，和高诚实 partner 完全匹配；但模型因为不相信低诚实对象而投得更少，最终错过了一部分正收益。

所以这个差异可以被理解为：

> 模型使用 orthogonal honesty cue 的行为代价，或者低诚实信号导致的机会成本。

谨慎一点说，这不是“诚实本身的客观价值”，而是当 honesty 和 payoff 被人为拆开时，模型仍把 honesty 当成 cooperative value proxy 所产生的代价。

## 目前最好的 story

一个比较清楚的论文故事是：

> LLMs do not merely follow cheap talk in repeated trust games. They strongly track revealed payoff structure. However, when factual honesty is made observable and orthogonal to payoff, LLMs still use honesty as a proxy for cooperative value. This can improve reliance on honest partners, but it can also reduce payoff with low-honesty partners whose actual return policy is equally fair.

中文版本：

> 大模型在重复信任博弈中并不会简单被漂亮话牵着走；它们非常依赖实际行为和收益证据。但当“是否说真话”作为一个可核验的社会信号出现时，即使它和真实返还收益被正交操纵，模型仍会把 honesty 当作合作价值的代理信号。这种偏置会改变逐轮投资，并在低诚实但同样返还的对象身上造成收益损失。

## 主要限制

1. 当前多数实验还是 API simulation，不是真实人类被试。
2. V1-V5 里很多 history 是一次性呈现，容易让模型做 table reading。
3. V8 已经改成 trial-by-trial，但目前只完整跑通了 sequential condition。
4. V8 的 evidence-only 对照在 MiniMax-M2.7 上容易诱发长篇推理并无法稳定返回 JSON，暂不作为正式结果解释。
5. 需要跨模型复现：GPT、Claude、Gemini、Qwen、DeepSeek、MiniMax。
6. V9 已把“返还反馈本身”“可核验诚实性”“语言风格”和“投资收益”拆成设计条件，并已跑完整 sequential 信号；但 evidence-only 还没有稳定进入正式结果。

## 下一步建议

1. 修 V9 evidence-only：把输出限制进一步收紧，必要时改成每轮单独 prompt + 更短字段，先追求稳定 JSON。
2. 用 V9 的 trial-level data 做模型：`investment_t ~ cumulative_truth_rate_before + cumulative_return_rate_before + previous_payoff + trial + condition + model`。
3. 再做跨模型复现：至少 MiniMax、Qwen、DeepSeek、GPT、Claude。
4. 如果要做人类实验，可以把 V9 改成真实 bonus + trial-by-trial investment，检验人类是否也会因为低诚实但公平返还而少赚。

## 主要文件

- `output/`, `scripts/`, `conditions/`, `prompts/`: V1 pilot。
- `v2_average_control/`: average-return controlled policy-structure experiment。
- `v3_noisy_policy/`: noisy policy and language-frame experiment。
- `v4_clean_wtp/`: yoked-history WTP and investment experiment。
- `v5_controllability/`: controllability and strategic-opportunity experiment。
- `v6_advice_trust_transfer/`: honesty/payoff separation and advice-to-trust transfer experiment。
- `v7_payoff_matched_honesty/`: payoff-matched honesty-transfer experiment。
- `v8_trial_by_trial_honesty_bias/`: trial-by-trial honesty bias and payoff-cost experiment。
- `v9_honesty_source_control/`: formal V8 extension with honesty, return-policy, presentation, orthogonality, and control conditions。
- `v9b_instruction_control/`: instruction-control follow-up testing whether explicit orthogonality behaves like a causal cue。
- `repeated_trust_games_v1-4_report.html`: V1-V4 visual report。
- `experiment_report_visual.html`: V1-V4 integrated visual report。

## Reproducibility Notes

Set the API key in the shell only:

```powershell
$env:MINIMAX_API_KEY="YOUR_KEY"
```

Do not write API keys into scripts, prompts, JSON files, reports, or README files.
