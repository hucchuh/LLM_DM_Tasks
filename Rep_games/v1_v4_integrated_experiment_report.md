# 在重复信任博弈中，大语言模型是听漂亮话还是看实际投资行为？

日期：2026-05-21  
模型：MiniMax-M2.7  
说明：目前所有实验都是 API 层面的 LLM-as-subject pilot，不是真实人类被试实验。

## 1. 研究问题

这个系列实验想回答一个具体问题：

> 当 partner 说的话和实际行为可能冲突时，LLM 在重复信任/投资场景中究竟更依赖 verbal cue，还是更依赖 observed action / revealed policy？

这里的关键不是笼统问“LLM 有没有 theory of mind”，而是把问题压到一个更可操作的层面：

- LLM 是否会根据 partner 的实际返还行为更新信任？
- LLM 是否只是追踪总体平均返还，还是能识别 stake-dependent policy、repairing trend、deteriorating trend？
- 当 cheap talk 与行为证据分离时，语言是否会改变模型的 costly choice，例如 willingness to pay 和下一轮投资？

四个版本的递进逻辑是：

| 版本 | 核心目的 | 主要修正 |
|---|---|---|
| V1 | 先看 LLM 是否被语言牵引，还是看实际返还 | 建立初步现象 |
| V2 | 控制 average return，测试是否识别行为结构 | 排除“只看均值”的解释 |
| V3 | 加入 noisy histories 和语言条件 | 初步测试语言是否有独立效应 |
| V4 | 用 yoked histories + WTP choice 做更干净实验 | 排除 demand cue 和显性估计任务 |

## 2. 总体结论

四个版本的结果相当一致：

1. LLM 对 partner 的信任判断强烈跟随实际行为，而不是单纯跟随温暖、承诺或道歉。
2. LLM 不只是压缩为一个 global trust impression；它能识别更结构化的 partner policy，例如 high-stake betrayal、repairing trend 和 deteriorating trend。
3. 语言并非完全没有作用，但作用小、不稳定，并且更多体现在 trust rating 或 willingness to pay，而不是稳定改变具体的风险暴露。
4. 当主任务改成 costly choice，不再显式要求估计均值或报告 message/behavior weight 后，behavior pattern 仍然解释主要方差。

现有数据中的一个简洁量化结果：

| 数据集 | 因变量 | behavior pattern R² | language frame R² |
|---|---:|---:|---:|
| V3 | trust rating | 0.593 | 0.032 |
| V3 | predicted high-low gap | 0.951 | 0.001 |
| V3 | high-stake investment | 0.647 | 0.008 |
| V4 | WTP | 0.513 | 0.016 |
| V4 | investment fraction | 0.589 | 0.001 |
| V4 | trust rating | 0.526 | 0.012 |

这说明目前最稳的 story 是：

> LLM 在重复互动中形成的不是单一“好/坏人”印象，而是对 partner policy 的结构化表征；cheap talk 可以局部改变社会性评价或继续互动意愿，但很难覆盖 revealed behavior 对 costly choice 的影响。

## 3. V1：开放式 pilot

### 为什么做

V1 的目的很简单：先验证这个范式有没有信号。我们构造不同 partner 类型，让语言和行为有时一致、有时冲突，观察模型下一轮投资、预测返还和信任评分。

核心问题是：

> LLM 会被 warm promise / apology 拉高信任，还是会根据实际返还更新判断？

### 实验设计

V1 有 6 类 partner，每类 4 次重复，共 24 个 trial，成功 23 个。

| partner type | 语言特征 | 行为特征 |
|---|---|---|
| honest_cooperator | 温暖、合作承诺 | 稳定公平返还 |
| charming_under_returner | 温暖承诺和解释 | 稳定偏低返还 |
| cautious_reliable | 谨慎、不强承诺 | 稳定公平返还 |
| strategic_opportunist | 合作语言，尤其高赌注时 | low stake 公平，high stake 剥削 |
| noisy_repairing | 道歉并补偿 | 偶尔低返还，随后真实修复 |
| apology_only_exploiter | 道歉和解释 | 低返还，无真实补偿 |

模型看到的是逐轮 history：每轮 stake、partner message、投资额、partner received、partner returned。模型没有被直接给出平均值，但可以从每轮记录计算。

主要因变量：

- `investment_next`
- `predicted_return_fraction_next`
- `trust_rating`
- `confidence`

### 结果

V1 最强结果是 trust rating 与 observed average return 高度相关：

- trial-level: r = 0.878
- partner-type mean: r = 0.992

关键均值：

| partner type | mean return | high-stake return | trust | next investment |
|---|---:|---:|---:|---:|
| honest_cooperator | 0.503 | 0.506 | 78.25 | 10.00 |
| cautious_reliable | 0.502 | 0.499 | 70.25 | 10.00 |
| noisy_repairing | 0.481 | 0.481 | 68.75 | 10.00 |
| strategic_opportunist | 0.400 | 0.236 | 51.00 | 8.50 |
| charming_under_returner | 0.331 | 0.326 | 38.25 | 4.50 |
| apology_only_exploiter | 0.283 | 0.272 | 27.67 | 1.67 |

### 解释

V1 说明模型明显不是只看 partner 说得好不好。`charming_under_returner` 和 `apology_only_exploiter` 语言并不差，但信任和投资都低。相反，`cautious_reliable` 语言谨慎，但行为可靠，仍获得高信任。

不过 V1 不能排除一个简单解释：模型可能只是看 average return。也就是说，它未必真的识别 partner policy，只是把所有历史压缩成一个均值。

### 为什么做 V2

V2 的目标就是控制 average return。只有把总体平均返还固定住，才能测试模型是否识别行为结构。

## 4. V2：控制 average return，测试 policy structure

### 为什么做

V1 的最大问题是不同 partner 的平均返还不同。V2 将所有条件的 observed average return 固定为 0.40，测试模型是否仍能区分 partner。

核心问题是：

> 如果总体平均返还完全一样，LLM 还会识别 high-stake betrayal、repairing trend 和 deteriorating trend 吗？

### 实验设计

V2 有 6 个条件，每个条件 6 次，共 36 个 trial，全部成功。

所有条件：

```text
average return fraction = 0.40
```

条件设计：

| 条件 | 映射含义 | 行为结构 |
|---|---|---|
| stable_warm | honest_cooperator | 每轮 0.40，温暖语言 |
| stable_neutral | cautious_reliable | 每轮 0.40，中性语言 |
| high_stake_betrayal | strategic_opportunist | low 返还高，high 返还低 |
| high_stake_generous | strategic_opportunist_mirror | low 返还低，high 返还高 |
| repairing_trend | noisy_repairing | 早期低，后期修复 |
| declining_trend | apology_only_exploiter | 早期高，后期下降 |

主要因变量：

- `global_trust_rating`
- `message_credibility`
- `policy_structure_rating`
- low / medium / high stake 下的 predicted return
- low / medium / high stake 下的 investment

### 结果

虽然所有条件均值都是 0.40，模型的 conditional prediction 和 investment 明显分化。

| 条件 | trust | pred low | pred high | high-low gap | invest high |
|---|---:|---:|---:|---:|---:|
| stable_neutral | 73.33 | 0.40 | 0.40 | 0.00 | 10 |
| stable_warm | 57.17 | 0.40 | 0.40 | 0.00 | 10 |
| high_stake_betrayal | 49.17 | 0.55 | 0.25 | -0.30 | 0 |
| high_stake_generous | 77.50 | 0.25 | 0.55 | +0.30 | 10 |
| repairing_trend | 59.50 | 0.558 | 0.633 | +0.075 | 10 |
| declining_trend | 35.00 | 0.227 | 0.198 | -0.028 | 0 |

### 解释

V2 强烈支持：LLM 不只是用 average return，而是在识别 return structure。最清楚的是 `high_stake_betrayal` 与 `high_stake_generous`：平均返还相同，但模型对 high stake 的预测和投资完全不同。

这个结果很重要，因为它说明模型可以形成对 partner policy 的条件化表征：

```text
不是“这个人平均返还 0.40”
而是“这个人在 high stake 更可能背叛 / 更可能慷慨”
```

### V2 的问题

V2 太像模式识别题。它直接问 low / medium / high stake 下的预测返还和投资，容易 cue 模型去算条件均值。并且每个条件的结构非常整齐，不够像自然互动。

### 为什么做 V3

V3 试图加入 noisy history 和语言 frame，测试在更接近真实互动的历史中，语言是否能产生独立影响。

## 5. V3：noisy policy + language frame

### 为什么做

V3 的目标是把两个因素拆开：

1. 行为结构：stable、strategic、repairing、deteriorating。
2. 语言框架：neutral、warm promise、apology/excuse。

核心问题是：

> 当 observed average return 仍保持 0.40，但行为更有噪声、语言条件也变化时，语言是否会改变信任、预测和投资？

### 实验设计

V3 是 4 × 3 factorial design：

- behavior pattern: `stable_moderate`, `strategic_opportunist`, `noisy_repairing`, `apology_only_exploiter`
- language frame: `neutral`, `warm_promise`, `apology_excuse`
- 每个 cell 6 次，共 72 trial，全部成功

每条 history 有 6 轮，平均返还控制在 0.40，但每轮返还加入 noise。

主要因变量：

- `trust_rating`
- low / medium / high stake 下的 predicted return
- low / medium / high stake 下的 investment
- `message_weight`
- `behavior_weight`

### 结果

行为结构仍然主导结果。

| behavior | observed high | predicted high | high-low gap | high investment | trust |
|---|---:|---:|---:|---:|---:|
| stable_moderate | 0.396 | 0.397 | -0.005 | 9.444 | 64.500 |
| strategic_opportunist | 0.252 | 0.251 | -0.299 | 3.333 | 44.722 |
| noisy_repairing | 0.499 | 0.553 | +0.222 | 9.722 | 65.944 |
| apology_only_exploiter | 0.298 | 0.273 | -0.160 | 1.444 | 36.389 |

语言主效应相对小：

| language | trust | predicted high | high investment |
|---|---:|---:|---:|
| neutral | 48.792 | 0.363 | 6.500 |
| warm_promise | 55.542 | 0.374 | 5.917 |
| apology_excuse | 54.333 | 0.369 | 5.542 |

模型自报的证据权重：

- `behavior_weight`: 79.556
- `message_weight`: 20.139

补充分析显示，V3 中 behavior pattern 对 `predicted_high_minus_low` 的 R² = 0.951，而 language frame 的 R² = 0.001。也就是说，high-low prediction gap 几乎完全由行为结构解释。

### 解释

V3 的结果支持一个更强的说法：模型不是只形成 global trust，而是形成了条件化 belief map。例如：

- `strategic_opportunist`: low stake 好，high stake 差，所以 high-low gap 为负。
- `noisy_repairing`: 后期/高赌注表现更好，所以 high-low gap 为正。
- `apology_only_exploiter`: 后期恶化，所以 high stake 投资被压低。

语言可能稍微提高 trust rating，但很少改变 predicted return 和 high-stake investment。

### V3 的 reviewer 问题

V3 后来被 reviewer 视角指出几个关键问题：

1. 没有真正做到 yoked histories。不同 language 条件重新抽了 noisy history，只是均值接近。
2. stake order 与时间顺序混淆。high stake 更常在后面，因此 high-stake effect 可能混入 recency/trend。
3. `apology_excuse` 不是外生语言操纵，它会根据前一轮低返还触发，因此语言本身携带行为信息。
4. `message_weight` 和 `behavior_weight` 会 cue 模型进入“研究者在测语言 vs 行为”的答题模式。
5. 同时询问 low/medium/high predicted return，仍然像显性的模式识别任务。

### 为什么做 V4

V4 的目标是做一个更干净的行为实验：

- 不问模型平均值。
- 不问 message/behavior 权重。
- 同一条 numeric history 复制成不同语言版本。
- 只问一个 upcoming stake。
- 把主要因变量改成 costly choice：是否继续、愿意付多少钱、下一轮投多少。

## 6. V4：clean yoked histories + willingness to pay

### 为什么做

V4 是目前最干净的一版。它把研究问题从“你认为 low/high 会返还多少”改为：

> 在相同行为证据下，cheap talk 是否改变模型愿意为继续互动付出的真实成本？

这比显性估计任务更接近行为实验。

### 实验设计

V4 是 4 × 4 × next-stake design，共 96 trial，全部成功。

因素：

| factor | levels |
|---|---|
| behavior pattern | stable_moderate, strategic_opportunist, noisy_repairing, deteriorating_exploiter |
| language frame | neutral_filler, warmth, promise, apology |
| next stake | low, medium, high |

关键控制：

- yoked histories：同一条 numeric history 复制成四个语言版本，只改 partner message。
- counterbalanced stake order：low/medium/high 不固定出现在早期或后期。
- exogenous language：promise 和 apology 不由前一轮返还触发。
- single next-stake probe：每个 trial 只问一个 upcoming stake。
- 主任务不问 predicted mean，也不问 message/behavior weight。

主要因变量：

- `continue_choice`
- `willingness_to_pay`: 0-10
- `next_investment`
- `investment_fraction`
- `trust_rating`

### 结果

V4 的行为主效应非常清楚。

| behavior | WTP | investment fraction | trust | continue rate |
|---|---:|---:|---:|---:|
| deteriorating_exploiter | 0.042 | 0.167 | 28.917 | 0.250 |
| noisy_repairing | 3.375 | 1.000 | 65.208 | 1.000 |
| stable_moderate | 1.333 | 0.964 | 62.792 | 1.000 |
| strategic_opportunist | 2.000 | 0.710 | 48.875 | 0.875 |

语言主效应弱且不稳定。

| language | WTP | investment fraction | trust |
|---|---:|---:|---:|
| neutral_filler | 1.583 | 0.725 | 55.208 |
| warmth | 1.625 | 0.689 | 49.583 |
| promise | 1.500 | 0.725 | 50.125 |
| apology | 2.042 | 0.702 | 50.875 |

behavior × next stake 的结果更能说明模型学到了 policy structure：

| behavior × next stake | policy next return | WTP | investment fraction | trust |
|---|---:|---:|---:|---:|
| deteriorating_exploiter / high | 0.25 | 0.000 | 0.000 | 26.875 |
| noisy_repairing / high | 0.55 | 3.750 | 1.000 | 62.750 |
| stable_moderate / high | 0.40 | 2.125 | 1.000 | 61.250 |
| strategic_opportunist / high | 0.25 | 2.125 | 0.487 | 39.375 |
| strategic_opportunist / low | 0.55 | 1.875 | 0.875 | 52.875 |

V4 的简单 R² 分析：

| 因变量 | behavior pattern R² | language frame R² | next stake R² |
|---|---:|---:|---:|
| WTP | 0.513 | 0.016 | 0.032 |
| investment fraction | 0.589 | 0.001 | 0.023 |
| trust rating | 0.526 | 0.012 | 0.031 |

### 解释

V4 最重要的结论是：

> 当 cheap talk 被严格 yoked 到相同行为历史上，语言很难系统性改变 costly choice；模型主要依据 observed behavior / partner policy 做选择。

但还有一个可挖的小现象：在 `strategic_opportunist` 条件中，apology 相对 neutral 的 WTP 提高较多：

- WTP: +1.667
- investment fraction: +0.050
- trust: +0.833

这暗示语言可能更容易改变“愿意继续互动/给对方一次机会”的社会性意愿，但不一定改变具体风险暴露。换句话说：

```text
cheap talk may move access willingness more than risk exposure
```

这个区分可能是后续 paper 的一个亮点。

## 7. 四版实验的递进逻辑

### 从 V1 到 V2

V1 发现 trust 与 observed return 强相关，但无法排除 average-return explanation。V2 控制平均返还，证明模型能识别结构化 policy。

### 从 V2 到 V3

V2 太整齐、太像数学题。V3 加入 noisy history 和语言条件，初步测试 cheap talk 的独立效应。但 V3 仍有 demand cue。

### 从 V3 到 V4

V3 的问题在于显性问了模型 prediction 和 evidence weight。V4 去掉这些问题，改成 costly choice，并实现 yoked histories 和 counterbalanced stake order。

### 当前最稳的理论解释

四版实验合起来支持：

1. LLM 能从 interaction history 中抽取 partner policy。
2. 这种 policy representation 至少包括：平均返还、stake sensitivity、trend、repair vs decline。
3. Verbal cue 对模型不是完全无效，但在有明确行为证据时作用弱。
4. 语言可能更影响 social continuation / WTP，而不是 conditional investment。

## 8. Reviewer 视角：可能的问题

以下是一个行为学/实验心理学 reviewer 可能会指出的问题。

### 8.1 内部效度问题

V1-V3 中存在不同程度的 demand characteristics。尤其是 V2/V3 直接询问 low/medium/high predicted return，会让模型进入显性模式识别任务，而不是自然互动决策。

V3 中 `message_weight` 和 `behavior_weight` 是很强的研究目的 cue。这个变量不能作为机制证据，只能作为 exploratory self-report。

V1 和 V3 中某些语言是 contingent language，例如低返还后出现道歉。这使语言本身携带行为信息，不是纯 cheap talk 操纵。

V2/V3 中 stake order 和 time order 没有完全拆开。V4 已经修正了这一点。

### 8.2 构念问题

目前的 `trust_rating`、`WTP`、`investment_fraction` 是三个不同层面的变量：

- `trust_rating`: 主观评价。
- `WTP`: 愿意继续互动的 access value。
- `investment_fraction`: 具体风险暴露。

这些变量不能混在一起解释。V4 最有意思的是它们可能发生分离：语言可能影响 WTP，但不明显影响 investment fraction。

### 8.3 外部效度问题

当前只有 MiniMax-M2.7 一个模型，不能推广到 LLM 一般行为。需要至少加入 GPT、Claude、Gemini、Qwen、DeepSeek 等多个模型。

当前是 API pilot，不是真实人类实验。若目标是 NHB/NC 水平，最终需要人类被试作对照，或者至少需要把 LLM 行为与人类已知 repeated trust game / cheap talk 文献接上。

当前 WTP 是 hypothetical WTP，不是真实激励。对 LLM 来说这不是问题，但如果迁移到人类实验，必须用真实 bonus 或 incentive-compatible design。

### 8.4 统计问题

目前主要是均值和简单 R²。正式分析应使用 trial-level model：

```text
WTP ~ behavior_pattern * language_frame + next_stake + (1 | history_id)
investment_fraction ~ behavior_pattern * language_frame + next_stake + (1 | history_id)
trust_rating ~ behavior_pattern * language_frame + next_stake + (1 | history_id)
```

如果跨模型扩展，还应加入：

```text
(1 | model)
```

或者把 model 作为固定因子，检验不同模型是否有不同 cheap-talk susceptibility。

### 8.5 机制解释问题

现在不能直接声称“LLM 像人一样更新信任”。更谨慎的说法是：

> 在给定 repeated interaction records 后，LLM 的选择与一种 revealed-policy inference 相一致。

如果要声称 belief updating，需要更动态的 sequential design：每轮后记录选择和预测，而不是一次性呈现完整 history。

## 9. 建议下一步

### V5A：多模型 replication

用 V4 protocol 直接扩展到多个模型：

- MiniMax-M2.7
- GPT-5.5 或 GPT-5 系列
- Claude
- Gemini
- Qwen / DeepSeek

目标不是只看谁更“聪明”，而是比较：

- behavior sensitivity
- cheap-talk susceptibility
- WTP vs investment dissociation
- strategic opportunist 条件下是否被 apology 拉高 WTP

### V5B：加入 held-out prediction，但不要放进主 prompt

主任务仍然只问 costly choice。另开一个 separate probe：

- 给同样 history，问下一轮实际返还预测。
- 或者给隐藏第 7 轮，评估模型预测误差。

这样可以区分：

```text
belief accuracy
choice policy
social trust
```

### V5C：人类对照实验

用 V4 的 yoked histories 给真实被试：

- 真实 WTP bonus
- 真实下一轮投资
- cheap talk yoked manipulation

关键比较：

> 人类是否比 LLM 更容易被 apology / warmth 拉动 WTP 或 investment？

如果人类比 LLM 更受 cheap talk 影响，story 是：

> LLMs may be less socially gullible than humans under explicit behavioral evidence.

如果 LLM 与人类相似，story 是：

> LLMs reproduce a human-like dissociation between revealed behavior and verbal repair.

### V5D：机制探针

不要在主任务里问 message_weight。可以在完成 choice 后另开独立 context，问模型解释或分类 partner policy。

更好的机制 probe 是：

- partner policy classification
- high-stake betrayal detection
- repair vs apology-only classification
- counterfactual choice under matched expected value

## 10. 当前可发表 story 的雏形

一个可能的标题方向：

> Revealed behavior dominates cheap talk in large language model trust decisions

或者更具体：

> Large language models infer partner policy rather than global trust in repeated investment games

目前最强的 claim：

> LLMs are sensitive to structured partner policies in repeated social exchange. When cheap talk is yoked to identical behavior, language has weak and unstable effects on costly choice, while revealed behavior explains most variance in WTP, investment, and trust.

目前还不能强 claim：

- LLM 具有人类式 theory of mind。
- LLM 真实形成稳定社会信念。
- cheap talk 完全无效。
- 这些结论能推广到所有模型。

这份 pilot 已经有一个不错的方向：从“LLM 是否有 ToM”转向“LLM 在 social decision task 中如何整合语言信号与行为证据”。这个问题更具体，也更容易做成可检验的实验范式。
